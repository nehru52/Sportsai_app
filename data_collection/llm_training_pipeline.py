"""
LLM Training Data Pipeline for Biomechanical Corrections
Generates synthetic training data and manages expert-labeled corrections
Integrates FIVB benchmarks with coaching feedback
"""

import json
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import random
from pathlib import Path

@dataclass
class BiomechanicalSample:
    joint_angles: Dict[str, float]
    joint_velocities: Dict[str, float]
    temporal_features: Dict[str, float]
    spatial_features: Dict[str, float]
    context: Dict[str, str]
    assessment: str
    deviations: Dict[str, float]
    correction: str
    drill: str
    expert_notes: Optional[str] = None

@dataclass
class TrainingPair:
    input_features: Dict[str, any]
    target_output: Dict[str, str]
    metadata: Dict[str, any]
    quality_score: float = 0.0

class FIVBBiomechanicalData:
    """FIVB biomechanical benchmarks and ranges"""
    
    def __init__(self):
        # FIVB Level II biomechanical standards
        self.elite_benchmarks = {
            'spike': {
                'approach_angle': {'mean': 45.2, 'std': 3.1, 'range': (40, 50)},
                'elbow_flexion': {'mean': 166.4, 'std': 8.2, 'range': (150, 180)},
                'torso_extension': {'mean': 159.8, 'std': 12.4, 'range': (135, 175)},
                'knee_flexion': {'mean': 118.7, 'std': 9.3, 'range': (100, 135)},
                'shoulder_rotation': {'mean': 142.1, 'std': 11.7, 'range': (120, 165)},
                'wrist_snap_velocity': {'mean': 8.2, 'std': 1.1, 'range': (6.0, 10.5)},
                'approach_velocity': {'mean': 4.8, 'std': 0.4, 'range': (4.0, 5.5)},
                'jump_height': {'mean': 0.67, 'std': 0.08, 'range': (0.55, 0.80)}
            },
            'serve': {
                'toss_height': {'mean': 2.1, 'std': 0.3, 'range': (1.5, 2.8)},
                'elbow_flexion': {'mean': 145.2, 'std': 7.8, 'range': (130, 160)},
                'shoulder_rotation': {'mean': 158.3, 'std': 9.1, 'range': (140, 175)},
                'torso_rotation': {'mean': 89.7, 'std': 8.2, 'range': (75, 105)},
                'wrist_velocity': {'mean': 12.4, 'std': 1.8, 'range': (9.0, 16.0)},
                'ball_velocity': {'mean': 23.8, 'std': 2.1, 'range': (19.0, 28.0)}
            },
            'block': {
                'penetration_angle': {'mean': 23.1, 'std': 3.2, 'range': (18, 28)},
                'hand_position_height': {'mean': 0.85, 'std': 0.06, 'range': (0.75, 0.95)},
                'reaction_time': {'mean': 0.18, 'std': 0.03, 'range': (0.12, 0.25)},
                'jump_height': {'mean': 0.52, 'std': 0.07, 'range': (0.40, 0.65)}
            },
            'dig': {
                'platform_angle': {'mean': 28.3, 'std': 4.1, 'range': (20, 35)},
                'arm_extension': {'mean': 142.7, 'std': 8.9, 'range': (125, 160)},
                'reaction_time': {'mean': 0.22, 'std': 0.04, 'range': (0.15, 0.30)}
            }
        }
        
        # Position-specific variations
        self.position_variations = {
            'middle': {
                'spike': {'approach_angle': +2.1, 'jump_height': +0.03, 'approach_velocity': +0.2},
                'block': {'penetration_angle': +1.5, 'jump_height': +0.02}
            },
            'opposite': {
                'spike': {'approach_angle': -1.8, 'torso_extension': +3.2},
                'serve': {'ball_velocity': +1.2, 'toss_height': +0.15}
            },
            'outside': {
                'spike': {'approach_velocity': +0.15, 'shoulder_rotation': +2.1},
                'reception': {'platform_angle': -1.5}
            },
            'libero': {
                'dig': {'reaction_time': -0.03, 'platform_angle': +2.1},
                'reception': {'platform_angle': +1.8}
            },
            'setter': {
                'set': {'hand_position_height': +0.05}  # Higher setting position
            }
        }
    
    def get_elite_benchmark(self, technique: str, joint: str, position: str = 'general') -> Dict:
        """Get elite benchmark for specific technique and joint"""
        
        base_benchmark = self.elite_benchmarks.get(technique, {}).get(joint, {})
        
        if position in self.position_variations and technique in self.position_variations[position]:
            variation = self.position_variations[position][technique]
            if joint in variation:
                # Apply position-specific variation
                modified_benchmark = base_benchmark.copy()
                if 'mean' in modified_benchmark:
                    modified_benchmark['mean'] += variation[joint]
                return modified_benchmark
        
        return base_benchmark
    
    def generate_deviation_assessment(self, measured_value: float, benchmark: Dict) -> Tuple[str, float]:
        """Generate assessment based on deviation from benchmark"""
        
        if not benchmark or 'mean' not in benchmark:
            return 'unknown', 0.0
        
        mean = benchmark['mean']
        std = benchmark.get('std', 5.0)
        
        deviation = measured_value - mean
        z_score = deviation / std
        
        # Assessment categories
        if abs(z_score) <= 0.5:
            assessment = 'elite'
            severity = 0.0
        elif abs(z_score) <= 1.0:
            assessment = 'good'
            severity = abs(z_score) * 0.3
        elif abs(z_score) <= 1.5:
            assessment = 'needs_improvement'
            severity = abs(z_score) * 0.5
        else:
            assessment = 'significant_deviation'
            severity = min(abs(z_score) * 0.7, 1.0)
        
        return assessment, severity

class LLMTrainingDataGenerator:
    """Generate training data for LLM biomechanical corrections"""
    
    def __init__(self):
        self.fivb_data = FIVBBiomechanicalData()
        self.coaching_templates = self.load_coaching_templates()
        self.drill_database = self.load_drill_database()
        
        # Training data quality thresholds
        self.min_quality_score = 0.7
        self.max_deviation_threshold = 2.0
    
    def load_coaching_templates(self) -> Dict:
        """Load coaching correction templates"""
        
        return {
            'spike': {
                'elbow_flexion': {
                    'too_low': [
                        "Maintain 'bow and arrow' position longer during approach",
                        "Delay arm swing until last 0.2s before contact",
                        "Focus on elbow flexion during backswing phase"
                    ],
                    'too_high': [
                        "Start arm swing earlier in approach sequence",
                        "Reduce elbow flexion to allow faster arm acceleration",
                        "Practice timing of arm extension with jump"
                    ]
                },
                'torso_extension': {
                    'too_low': [
                        "Engage core to prevent 'sitting' during approach",
                        "Extend torso fully during jump phase",
                        "Practice arching back during arm swing"
                    ],
                    'too_high': [
                        "Maintain more upright torso position",
                        "Focus on forward lean rather than backward arch",
                        "Practice controlled torso rotation"
                    ]
                },
                'approach_angle': {
                    'too_low': [
                        "Increase approach angle for better momentum transfer",
                        "Start approach from wider position",
                        "Practice 45-degree angle approach"
                    ],
                    'too_high': [
                        "Reduce approach angle for more direct path",
                        "Focus on forward momentum over lateral movement",
                        "Practice straighter approach lines"
                    ]
                }
            },
            'serve': {
                'toss_height': {
                    'too_low': [
                        "Increase toss height by 20-30cm",
                        "Practice consistent toss to optimal height",
                        "Focus on upward toss motion"
                    ],
                    'too_high': [
                        "Reduce toss height for better timing control",
                        "Practice lower, more consistent toss",
                        "Focus on timing rather than height"
                    ]
                },
                'elbow_flexion': {
                    'too_low': [
                        "Increase elbow flexion during backswing",
                        "Practice 'bow and arrow' position",
                        "Focus on elbow loading phase"
                    ],
                    'too_high': [
                        "Reduce excessive elbow flexion",
                        "Practice more natural arm position",
                        "Focus on fluid motion over position"
                    ]
                }
            },
            'block': {
                'penetration_angle': {
                    'too_low': [
                        "Increase hand penetration over the net",
                        "Focus on pressing hands forward",
                        "Practice 'sealing' the net"
                    ],
                    'too_high': [
                        "Reduce hand penetration to avoid net violations",
                        "Focus on vertical hand position",
                        "Practice controlled penetration"
                    ]
                },
                'reaction_time': {
                    'too_slow': [
                        "Improve reading of attacker tendencies",
                        "Practice earlier timing cues",
                        "Focus on pre-jump preparation"
                    ],
                    'too_fast': [
                        "Delay jump timing for better timing",
                        "Focus on reading attacker arm swing",
                        "Practice patience in block timing"
                    ]
                }
            },
            'dig': {
                'platform_angle': {
                    'too_low': [
                        "Increase platform angle for better control",
                        "Focus on forearm angle",
                        "Practice platform stability"
                    ],
                    'too_high': [
                        "Reduce platform angle for better ball control",
                        "Focus on flatter platform",
                        "Practice angle adjustment"
                    ]
                },
                'reaction_time': {
                    'too_slow': [
                        "Improve reading of attacker arm swing",
                        "Practice earlier defensive positioning",
                        "Focus on visual tracking"
                    ],
                    'too_fast': [
                        "Delay defensive movement for better timing",
                        "Focus on controlled approach to ball",
                        "Practice patience in defensive positioning"
                    ]
                }
            }
        }
    
    def load_drill_database(self) -> Dict:
        """Load drill database for corrections"""
        
        return {
            'spike': {
                'elbow_flexion': {
                    'too_low': [
                        "Wall blocks with delayed arm swing - focus on maintaining 90° elbow flexion until last 0.2s",
                        "Bow and arrow drill - practice loading position with partner resistance",
                        "Medicine ball throws - emphasize elbow flexion during throwing motion",
                        "Elastic band pulls - strengthen elbow flexors with sport-specific movement"
                    ],
                    'too_high': [
                        "Quick arm swings - practice rapid extension from loaded position",
                        "Timing drill with metronome - synchronize arm swing with approach",
                        "Jump rope with arm swings - coordinate timing of arm and leg movements",
                        "Video analysis - compare arm swing timing with elite examples"
                    ]
                },
                'torso_extension': {
                    'too_low': [
                        "Superman holds - strengthen lower back for better extension",
                        "Medicine ball overhead throws - practice full torso extension",
                        "Yoga cobra pose - improve spine flexibility and extension",
                        "Partner-assisted extensions - feel proper torso position"
                    ],
                    'too_high': [
                        "Core strengthening - improve control during extension",
                        "Balance board exercises - maintain upright position during instability",
                        "Wall sits with arm swings - practice controlled torso movement",
                        "Mirror work - visualize and correct torso position"
                    ]
                }
            },
            'serve': {
                'toss_height': {
                    'too_low': [
                        "Toss and catch - practice consistent height without serving",
                        "Wall target practice - aim toss to specific height markers",
                        "Rhythm training - establish consistent toss timing",
                        "Partner toss feedback - get external validation of toss height"
                    ],
                    'too_high': [
                        "Lower toss targets - practice tossing to reduced height",
                        "Quick serve drill - reduce time between toss and contact",
                        "No-toss serves - practice serving with minimal toss",
                        "Metronome training - establish optimal timing rhythm"
                    ]
                }
            },
            'block': {
                'penetration_angle': {
                    'too_low': [
                        "Wall penetration drill - practice pressing hands over wall",
                        "Partner resistance - practice penetration against resistance",
                        "Net touch drill - focus on reaching over net",
                        "Mirror penetration - visualize proper hand position"
                    ],
                    'too_high': [
                        "Net awareness drill - practice close-to-net positioning",
                        "Controlled penetration - focus on legal hand position",
                        "Referee feedback - get external validation of penetration",
                        "Slow-motion blocking - practice controlled penetration"
                    ]
                }
            },
            'dig': {
                'platform_angle': {
                    'too_low': [
                        "Platform angle drill - practice with angled targets",
                        "Forearm strengthening - improve platform stability",
                        "Ball control drill - focus on consistent platform angle",
                        "Partner feedback - get external validation of angle"
                    ],
                    'too_high': [
                        "Flat platform drill - practice reducing angle",
                        "Ball trajectory drill - adjust angle for different attacks",
                        "Video analysis - compare platform angle with elite examples",
                        "Target practice - aim digs to specific locations"
                    ]
                }
            }
        }
    
    def generate_synthetic_training_data(self, technique: str, num_samples: int = 1000) -> List[TrainingPair]:
        """Generate synthetic training data based on FIVB benchmarks"""
        
        training_pairs = []
        
        for _ in range(num_samples):
            # Generate random but realistic biomechanical data
            sample = self.generate_biomechanical_sample(technique)
            
            # Create training pair
            training_pair = self.create_training_pair(sample, technique)
            
            if training_pair.quality_score >= self.min_quality_score:
                training_pairs.append(training_pair)
        
        return training_pairs
    
    def generate_biomechanical_sample(self, technique: str) -> BiomechanicalSample:
        """Generate realistic biomechanical sample"""
        
        # Select random position
        positions = ['middle', 'opposite', 'outside', 'libero', 'setter', 'general']
        position = random.choice(positions)
        
        # Generate joint angles with realistic variations
        joint_angles = {}
        joint_velocities = {}
        
        if technique in self.fivb_data.elite_benchmarks:
            for joint, benchmark in self.fivb_data.elite_benchmarks[technique].items():
                # Generate measurement with realistic error
                mean = benchmark['mean']
                std = benchmark['std']
                
                # Add some measurement noise and potential deviations
                measurement_noise = np.random.normal(0, std * 0.3)  # 30% of benchmark std
                systematic_error = np.random.normal(0, std * 0.2)   # 20% systematic bias
                
                measured_value = mean + measurement_noise + systematic_error
                
                joint_angles[joint] = measured_value
                joint_velocities[joint] = np.random.normal(0, std * 0.1)  # Small velocity variations
        
        # Generate temporal features
        temporal_features = self.generate_temporal_features(technique)
        
        # Generate spatial features
        spatial_features = self.generate_spatial_features(technique)
        
        # Generate context
        context = {
            'technique': technique,
            'position': position,
            'set_tempo': random.choice(['first_tempo', 'second_tempo', 'high_ball']),
            'attack_zone': str(random.randint(1, 9)),
            'game_phase': random.choice(['side_out', 'transition', 'point_scoring']),
            'competition_level': random.choice(['training', 'national', 'international']),
            'player_experience': random.choice(['junior', 'college', 'professional', 'elite'])
        }
        
        # Generate assessment and deviations
        assessment = 'good'  # Default
        deviations = {}
        
        # Calculate deviations from benchmarks
        for joint, measured_value in joint_angles.items():
            benchmark = self.fivb_data.get_elite_benchmark(technique, joint, position)
            if benchmark:
                assessment_result, severity = self.fivb_data.generate_deviation_assessment(measured_value, benchmark)
                if severity > 0.1:  # Significant deviation
                    deviations[joint] = measured_value - benchmark['mean']
                    if severity > 0.3:  # Update overall assessment
                        assessment = 'needs_improvement'
        
        # Generate correction and drill recommendations
        correction = self.generate_correction(technique, deviations, context)
        drill = self.generate_drill(technique, deviations, context)
        
        return BiomechanicalSample(
            joint_angles=joint_angles,
            joint_velocities=joint_velocities,
            temporal_features=temporal_features,
            spatial_features=spatial_features,
            context=context,
            assessment=assessment,
            deviations=deviations,
            correction=correction,
            drill=drill
        )
    
    def generate_temporal_features(self, technique: str) -> Dict[str, float]:
        """Generate temporal features for the technique"""
        
        if technique == 'spike':
            return {
                'approach_duration': np.random.normal(1.2, 0.2),  # seconds
                'arm_swing_duration': np.random.normal(0.3, 0.05),
                'contact_to_landing': np.random.normal(0.4, 0.1),
                'total_jump_time': np.random.normal(0.7, 0.1)
            }
        elif technique == 'serve':
            return {
                'toss_to_contact': np.random.normal(0.8, 0.1),
                'arm_swing_duration': np.random.normal(0.4, 0.08),
                'ball_flight_time': np.random.normal(0.6, 0.1)
            }
        elif technique == 'block':
            return {
                'reaction_time': np.random.normal(0.18, 0.03),
                'jump_duration': np.random.normal(0.5, 0.08),
                'penetration_time': np.random.normal(0.3, 0.05)
            }
        elif technique == 'dig':
            return {
                'reaction_time': np.random.normal(0.22, 0.04),
                'platform_prep_time': np.random.normal(0.15, 0.03),
                'ball_contact_time': np.random.normal(0.05, 0.01)
            }
        
        return {}
    
    def generate_spatial_features(self, technique: str) -> Dict[str, float]:
        """Generate spatial features for the technique"""
        
        if technique == 'spike':
            return {
                'approach_distance': np.random.normal(3.2, 0.5),  # meters
                'jump_peak_height': np.random.normal(0.67, 0.08),
                'contact_height': np.random.normal(2.8, 0.2),
                'horizontal_velocity': np.random.normal(3.1, 0.4)
            }
        elif technique == 'serve':
            return {
                'toss_vertical_deviation': np.random.normal(0.05, 0.02),  # meters
                'toss_horizontal_deviation': np.random.normal(0.08, 0.03),
                'contact_height': np.random.normal(2.9, 0.15),
                'service_line_distance': np.random.normal(0.3, 0.1)
            }
        elif technique == 'block':
            return {
                'net_distance': np.random.normal(0.05, 0.02),  # meters from net
                'hand_height_above_net': np.random.normal(0.25, 0.05),
                'lateral_movement': np.random.normal(0.8, 0.3),
                'vertical_penetration': np.random.normal(0.12, 0.03)
            }
        elif technique == 'dig':
            return {
                'platform_height': np.random.normal(0.25, 0.05),  # meters from ground
                'lateral_range': np.random.normal(1.2, 0.3),
                'forward_backward_range': np.random.normal(0.8, 0.2),
                'platform_stability': np.random.normal(0.85, 0.1)
            }
        
        return {}
    
    def generate_correction(self, technique: str, deviations: Dict[str, float], context: Dict[str, str]) -> str:
        """Generate coaching correction based on deviations"""
        
        if not deviations:
            return "Technique shows good biomechanical alignment with elite standards."
        
        corrections = []
        
        for joint, deviation in deviations.items():
            if joint in self.coaching_templates.get(technique, {}):
                direction = 'too_low' if deviation < 0 else 'too_high'
                if direction in self.coaching_templates[technique][joint]:
                    templates = self.coaching_templates[technique][joint][direction]
                    correction = random.choice(templates)
                    
                    # Add contextual information
                    if context.get('set_tempo') == 'first_tempo' and technique == 'spike':
                        correction += " Given the fast tempo, focus on timing adjustments."
                    
                    if context.get('attack_zone') in ['1', '2'] and technique == 'spike':
                        correction += " For front court attacks, emphasize approach mechanics."
                    
                    corrections.append(correction)
        
        return " ".join(corrections) if corrections else "Focus on maintaining consistent technique."
    
    def generate_drill(self, technique: str, deviations: Dict[str, float], context: Dict[str, str]) -> str:
        """Generate specific drill recommendations"""
        
        if not deviations:
            return "Continue with current training program focusing on consistency."
        
        drills = []
        
        for joint, deviation in deviations.items():
            if joint in self.drill_database.get(technique, {}):
                direction = 'too_low' if deviation < 0 else 'too_high'
                if direction in self.drill_database[technique][joint]:
                    drill_options = self.drill_database[technique][joint][direction]
                    drill = random.choice(drill_options)
                    
                    # Add contextual modifications
                    if context.get('player_experience') == 'junior':
                        drill += " Start with 10 repetitions and gradually increase."
                    elif context.get('player_experience') == 'elite':
                        drill += " Perform at game speed with immediate feedback."
                    
                    drills.append(drill)
        
        return " ".join(drills) if drills else "Incorporate technique-specific drills."
    
    def create_training_pair(self, sample: BiomechanicalSample, technique: str) -> TrainingPair:
        """Create training pair from biomechanical sample"""
        
        # Input features
        input_features = {
            'joint_angles': sample.joint_angles,
            'joint_velocities': sample.joint_velocities,
            'temporal_features': sample.temporal_features,
            'spatial_features': sample.spatial_features,
            'context': sample.context,
            'assessment': sample.assessment,
            'deviations': sample.deviations
        }
        
        # Target output
        target_output = {
            'correction': sample.correction,
            'drill': sample.drill,
            'assessment': sample.assessment,
            'priority': self.calculate_priority(sample.deviations),
            'timeline': self.estimate_timeline(sample.deviations, sample.context)
        }
        
        # Metadata
        metadata = {
            'technique': technique,
            'generated_at': datetime.now().isoformat(),
            'data_source': 'synthetic_fivb',
            'quality_indicators': {
                'deviation_severity': self.calculate_deviation_severity(sample.deviations),
                'context_completeness': self.calculate_context_completeness(sample.context),
                'biomechanical_validity': self.validate_biomechanical_data(sample)
            }
        }
        
        # Quality score
        quality_score = self.calculate_quality_score(sample, input_features, target_output)
        
        return TrainingPair(
            input_features=input_features,
            target_output=target_output,
            metadata=metadata,
            quality_score=quality_score
        )
    
    def calculate_priority(self, deviations: Dict[str, float]) -> str:
        """Calculate correction priority based on deviations"""
        
        if not deviations:
            return 'low'
        
        max_deviation = max(abs(dev) for dev in deviations.values())
        
        if max_deviation > 15:  # Degrees or significant units
            return 'high'
        elif max_deviation > 8:
            return 'medium'
        else:
            return 'low'
    
    def estimate_timeline(self, deviations: Dict[str, float], context: Dict[str, str]) -> str:
        """Estimate correction timeline based on deviations and context"""
        
        if not deviations:
            return 'maintenance'
        
        max_deviation = max(abs(dev) for dev in deviations.values())
        player_level = context.get('player_experience', 'intermediate')
        
        # Base timeline
        if max_deviation > 20:
            base_timeline = '8-12 weeks'
        elif max_deviation > 10:
            base_timeline = '4-8 weeks'
        else:
            base_timeline = '2-4 weeks'
        
        # Adjust for player level
        if player_level == 'elite':
            timeline = f"{base_timeline} (accelerated for elite athlete)"
        elif player_level == 'junior':
            timeline = f"{base_timeline} (extended for development)"
        else:
            timeline = base_timeline
        
        return timeline
    
    def calculate_deviation_severity(self, deviations: Dict[str, float]) -> float:
        """Calculate overall deviation severity"""
        
        if not deviations:
            return 0.0
        
        return max(abs(dev) for dev in deviations.values())
    
    def calculate_context_completeness(self, context: Dict[str, str]) -> float:
        """Calculate context completeness score"""
        
        required_fields = ['technique', 'position', 'set_tempo', 'game_phase']
        optional_fields = ['attack_zone', 'competition_level', 'player_experience']
        
        required_complete = sum(1 for field in required_fields if field in context and context[field])
        optional_complete = sum(1 for field in optional_fields if field in context and context[field])
        
        required_score = required_complete / len(required_fields)
        optional_score = optional_complete / len(optional_fields) if optional_fields else 0
        
        return 0.7 * required_score + 0.3 * optional_score
    
    def validate_biomechanical_data(self, sample: BiomechanicalSample) -> float:
        """Validate biomechanical data for consistency"""
        
        score = 1.0
        
        # Check for reasonable joint angle ranges
        for joint, angle in sample.joint_angles.items():
            if angle < -30 or angle > 200:  # Unreasonable angles
                score *= 0.8
        
        # Check for temporal consistency
        if sample.temporal_features:
            total_time = sum(sample.temporal_features.values())
            if total_time > 5.0:  # Unreasonably long
                score *= 0.7
        
        return score
    
    def calculate_quality_score(self, sample: BiomechanicalSample, input_features: Dict, target_output: Dict) -> float:
        """Calculate overall training pair quality score"""
        
        # Component scores
        context_score = self.calculate_context_completeness(sample.context)
        biomechanical_score = self.validate_biomechanical_data(sample)
        deviation_score = 1.0 - min(self.calculate_deviation_severity(sample.deviations) / 50, 1.0)
        
        # Weighted combination
        quality_score = (
            0.3 * context_score +
            0.3 * biomechanical_score +
            0.4 * deviation_score
        )
        
        return min(quality_score, 1.0)
    
    def export_training_data(self, training_pairs: List[TrainingPair], output_path: str, format: str = 'json'):
        """Export training data to file"""
        
        # Filter by quality
        high_quality_pairs = [pair for pair in training_pairs if pair.quality_score >= self.min_quality_score]
        
        if format == 'json':
            export_data = {
                'metadata': {
                    'total_samples': len(training_pairs),
                    'high_quality_samples': len(high_quality_pairs),
                    'techniques': list(set(pair.metadata['technique'] for pair in training_pairs)),
                    'generated_at': datetime.now().isoformat(),
                    'quality_threshold': self.min_quality_score
                },
                'training_pairs': [
                    {
                        'input': pair.input_features,
                        'target': pair.target_output,
                        'metadata': pair.metadata,
                        'quality_score': pair.quality_score
                    }
                    for pair in high_quality_pairs
                ]
            }
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        elif format == 'csv':
            # Flatten data for CSV export
            rows = []
            for pair in high_quality_pairs:
                row = {}
                
                # Flatten input features
                for key, value in pair.input_features.items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            row[f"input_{key}_{subkey}"] = subvalue
                    else:
                        row[f"input_{key}"] = value
                
                # Flatten target output
                for key, value in pair.target_output.items():
                    row[f"target_{key}"] = value
                
                # Add metadata
                row['quality_score'] = pair.quality_score
                row['technique'] = pair.metadata['technique']
                
                rows.append(row)
            
            df = pd.DataFrame(rows)
            df.to_csv(output_path, index=False)
        
        print(f"Exported {len(high_quality_pairs)} high-quality training pairs to {output_path}")

# Global training data generator
training_generator = LLMTrainingDataGenerator()

def generate_llm_training_dataset(techniques: List[str], samples_per_technique: int = 1000, 
                                output_dir: str = "C:/sportsai-backend/data/llm_training") -> str:
    """Generate complete LLM training dataset"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    all_training_pairs = []
    
    for technique in techniques:
        print(f"Generating training data for {technique}...")
        
        # Generate synthetic data
        technique_pairs = training_generator.generate_synthetic_training_data(technique, samples_per_technique)
        all_training_pairs.extend(technique_pairs)
        
        # Export technique-specific data
        technique_file = output_path / f"{technique}_training_data.json"
        training_generator.export_training_data(technique_pairs, str(technique_file))
    
    # Export combined dataset
    combined_file = output_path / "combined_training_data.json"
    training_generator.export_training_data(all_training_pairs, str(combined_file))
    
    print(f"Generated {len(all_training_pairs)} total training pairs")
    return str(combined_file)

def create_training_pair_from_analysis(biomechanical_data: Dict, tactical_context: Dict, 
                                     elite_comparison: Dict) -> Optional[TrainingPair]:
    """Create training pair from actual analysis data"""
    
    try:
        # Extract biomechanical features
        joint_angles = biomechanical_data.get('joint_angles', {})
        temporal_features = biomechanical_data.get('temporal_features', {})
        spatial_features = biomechanical_data.get('spatial_features', {})
        
        # Extract context
        context = {
            **tactical_context,
            'technique': biomechanical_data.get('technique', 'unknown'),
            'position': biomechanical_data.get('position', 'unknown'),
            'competition_level': tactical_context.get('competition_level', 'training')
        }
        
        # Calculate deviations from elite benchmarks
        deviations = {}
        for joint, measured_value in joint_angles.items():
            if joint in elite_comparison:
                elite_value = elite_comparison[joint].get('elite_mean', measured_value)
                deviations[joint] = measured_value - elite_value
        
        # Generate assessment
        if deviations:
            max_deviation = max(abs(dev) for dev in deviations.values())
            if max_deviation > 15:
                assessment = 'needs_improvement'
            elif max_deviation > 8:
                assessment = 'good'
            else:
                assessment = 'elite'
        else:
            assessment = 'good'
        
        # Create sample
        sample = BiomechanicalSample(
            joint_angles=joint_angles,
            joint_velocities=biomechanical_data.get('joint_velocities', {}),
            temporal_features=temporal_features,
            spatial_features=spatial_features,
            context=context,
            assessment=assessment,
            deviations=deviations,
            correction="Based on analysis data - see expert feedback",
            drill="Focus on identified biomechanical deviations",
            expert_notes="Generated from actual match analysis"
        )
        
        # Create training pair
        return training_generator.create_training_pair(sample, context['technique'])
        
    except Exception as e:
        print(f"Error creating training pair from analysis: {e}")
        return None
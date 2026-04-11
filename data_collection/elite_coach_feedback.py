"""
Elite Olympic-Level Coaching Feedback System
Integrates FIVB manuals, biomechanical research, and position-specific coaching
"""
import json
from typing import Dict, List, Optional
from elite_biomechanics import get_elite_benchmark, get_elite_coaching_cue
from elite_analyser import ELITE_COACHING_KNOWLEDGE, POSITION_ELITE_STANDARDS

class EliteCoachingEngine:
    """Olympic-level coaching feedback generator"""
    
    def __init__(self):
        self.coaching_knowledge = ELITE_COACHING_KNOWLEDGE
        self.position_standards = POSITION_ELITE_STANDARDS
        
    def generate_elite_feedback(self, analysis_results: dict, athlete_level: str = "intermediate", 
                              session_history: list = None, tournament_context: str = "training") -> dict:
        """Generate Olympic-level coaching feedback"""
        
        technique = analysis_results.get("technique", "unknown")
        position = analysis_results.get("position", "unknown")
        elite_comparisons = analysis_results.get("elite_comparisons", {})
        temporal_accuracy = analysis_results.get("temporal_accuracy", {})
        coaching_insights = analysis_results.get("coaching_insights", [])
        
        # Generate comprehensive feedback
        feedback = {
            "headline": self._generate_headline(analysis_results, athlete_level, tournament_context),
            "technical_analysis": self._generate_technical_analysis(analysis_results, technique, position),
            "biomechanical_breakdown": self._generate_biomechanical_breakdown(elite_comparisons, technique, position),
            "temporal_assessment": self._generate_temporal_assessment(temporal_accuracy, technique),
            "position_specific_feedback": self._generate_position_feedback(analysis_results, position),
            "elite_corrections": self._generate_elite_corrections(elite_comparisons, technique, position),
            "training_prescription": self._generate_training_prescription(analysis_results, athlete_level, session_history),
            "performance_projection": self._generate_performance_projection(analysis_results, athlete_level),
            "next_session_focus": self._determine_next_focus(analysis_results, session_history),
            "injury_prevention": self._generate_injury_prevention(analysis_results, technique, position),
            "competition_readiness": self._assess_competition_readiness(analysis_results, tournament_context)
        }
        
        return feedback
    
    def _generate_headline(self, analysis_results: dict, athlete_level: str, tournament_context: str) -> str:
        """Generate Olympic-level headline assessment"""
        
        olympic_readiness = analysis_results.get("olympic_readiness_score", 0)
        performance_percentile = analysis_results.get("performance_percentile", 0)
        position = analysis_results.get("position", "unknown")
        technique = analysis_results.get("technique", "unknown")
        
        # Context-specific headlines
        if tournament_context == "olympic_trial":
            if olympic_readiness >= 85:
                return f"OLYMPIC CALIBER: Your {technique} technique meets international standards for {position} position"
            elif olympic_readiness >= 70:
                return f"OLYMPIC POTENTIAL: Strong foundation with specific areas for elite-level refinement"
            else:
                return f"DEVELOPMENT NEEDED: Current technique requires significant improvement for Olympic consideration"
        
        elif tournament_context == "world_championship":
            if olympic_readiness >= 80:
                return f"WORLD CLASS: Your {technique} ranks in the {performance_percentile:.0f}th percentile globally"
            else:
                return f"CHAMPIONSHIP GAPS: Technical improvements needed for world-level competition"
        
        else:  # Training context
            if olympic_readiness >= 90:
                return f"ELITE STATUS: Your {technique} technique is Olympic-ready with {performance_percentile:.0f}th percentile performance"
            elif olympic_readiness >= 80:
                return f"ADVANCED LEVEL: Strong {technique} mechanics with minor refinements needed for elite competition"
            elif olympic_readiness >= 70:
                return f"SOLID FOUNDATION: Good {technique} technique requiring targeted improvements for next level"
            else:
                return f"FUNDAMENTAL WORK NEEDED: Your {technique} technique needs comprehensive development"
    
    def _generate_technical_analysis(self, analysis_results: dict, technique: str, position: str) -> dict:
        """Generate detailed technical analysis"""
        
        elite_comparisons = analysis_results.get("elite_comparisons", {})
        temporal_accuracy = analysis_results.get("temporal_accuracy", {})
        
        analysis = {
            "overall_assessment": "",
            "technical_strengths": [],
            "technical_weaknesses": [],
            "phase_specific_analysis": {},
            "biomechanical_efficiency": 0,
            "coordination_score": 0
        }
        
        # Overall assessment
        olympic_readiness = analysis_results.get("olympic_readiness_score", 0)
        if olympic_readiness >= 90:
            analysis["overall_assessment"] = "Olympic-level technique execution"
        elif olympic_readiness >= 80:
            analysis["overall_assessment"] = "Advanced technical proficiency"
        elif olympic_readiness >= 70:
            analysis["overall_assessment"] = "Solid technical foundation with room for improvement"
        else:
            analysis["overall_assessment"] = "Fundamental technical development required"
        
        # Technical strengths and weaknesses
        strengths = elite_comparisons.get("strengths", [])
        improvement_areas = elite_comparisons.get("improvement_areas", [])
        
        for strength in strengths[:3]:
            analysis["technical_strengths"].append(self._get_strength_description(strength, technique))
        
        for weakness in improvement_areas[:3]:
            analysis["technical_weaknesses"].append(self._get_weakness_description(weakness, technique))
        
        # Phase-specific analysis
        phases = analysis_results.get("phase_analysis", [])
        for phase in phases:
            phase_name = phase.get("name", "unknown")
            timing_score = phase.get("timing_score", 0)
            
            if timing_score >= 0.9:
                phase_assessment = "Elite timing execution"
            elif timing_score >= 0.8:
                phase_assessment = "Advanced timing coordination"
            elif timing_score >= 0.7:
                phase_assessment = "Good timing with minor adjustments needed"
            else:
                phase_assessment = "Timing requires significant improvement"
            
            analysis["phase_specific_analysis"][phase_name] = {
                "timing_assessment": phase_assessment,
                "timing_score": timing_score,
                "duration_deviation": abs(phase.get("duration", 0) - phase.get("target_duration", 0))
            }
        
        # Calculate biomechanical efficiency
        metric_comparisons = elite_comparisons.get("metric_comparisons", {})
        if metric_comparisons:
            scores = [comp.get("performance_score", 0) for comp in metric_comparisons.values()]
            analysis["biomechanical_efficiency"] = sum(scores) / len(scores) if scores else 0
        
        # Coordination score based on temporal accuracy
        if temporal_accuracy:
            analysis["coordination_score"] = temporal_accuracy.get("overall_timing_score", 0)
        
        return analysis
    
    def _generate_biomechanical_breakdown(self, elite_comparisons: dict, technique: str, position: str) -> dict:
        """Generate detailed biomechanical analysis"""
        
        breakdown = {
            "joint_specific_analysis": {},
            "power_generation_efficiency": 0,
            "movement_sequence_optimization": 0,
            "energy_transfer_analysis": "",
            "injury_risk_assessment": "",
            "biomechanical_recommendations": []
        }
        
        metric_comparisons = elite_comparisons.get("metric_comparisons", {})
        
        for metric, comparison in metric_comparisons.items():
            measured = comparison.get("measured", 0)
            target = comparison.get("target", 0)
            deviation = comparison.get("deviation", 0)
            percentile = comparison.get("percentile", 0)
            is_elite = comparison.get("is_elite", False)
            
            breakdown["joint_specific_analysis"][metric] = {
                "measured_value": measured,
                "olympic_target": target,
                "deviation_from_elite": deviation,
                "performance_percentile": percentile,
                "elite_status": "ELITE" if is_elite else "SUB-ELITE",
                "biomechanical_implication": self._get_biomechanical_implication(metric, deviation, technique)
            }
        
        # Power generation efficiency
        power_metrics = self._identify_power_metrics(technique)
        power_scores = []
        for metric in power_metrics:
            if metric in metric_comparisons:
                power_scores.append(metric_comparisons[metric].get("performance_score", 0))
        
        breakdown["power_generation_efficiency"] = sum(power_scores) / len(power_scores) if power_scores else 0
        
        # Movement sequence optimization
        sequence_metrics = self._identify_sequence_metrics(technique)
        sequence_scores = []
        for metric in sequence_metrics:
            if metric in metric_comparisons:
                sequence_scores.append(metric_comparisons[metric].get("performance_score", 0))
        
        breakdown["movement_sequence_optimization"] = sum(sequence_scores) / len(sequence_scores) if sequence_scores else 0
        
        # Energy transfer analysis
        if breakdown["power_generation_efficiency"] >= 0.9:
            breakdown["energy_transfer_analysis"] = "Excellent energy transfer from ground to ball contact"
        elif breakdown["power_generation_efficiency"] >= 0.8:
            breakdown["energy_transfer_analysis"] = "Good energy transfer with minor inefficiencies"
        else:
            breakdown["energy_transfer_analysis"] = "Significant energy leaks in movement sequence"
        
        # Injury risk assessment
        breakdown["injury_risk_assessment"] = self._assess_injury_risk(metric_comparisons, technique)
        
        # Biomechanical recommendations
        breakdown["biomechanical_recommendations"] = self._generate_biomechanical_recommendations(metric_comparisons, technique, position)
        
        return breakdown
    
    def _generate_temporal_assessment(self, temporal_accuracy: dict, technique: str) -> dict:
        """Generate temporal timing assessment"""
        
        assessment = {
            "overall_timing_score": 0,
            "phase_timing_analysis": {},
            "rhythm_coordination": "",
            "temporal_efficiency": 0,
            "timing_recommendations": []
        }
        
        if not temporal_accuracy:
            return assessment
        
        assessment["overall_timing_score"] = temporal_accuracy.get("overall_timing_score", 0)
        
        # Phase-specific timing analysis
        if "phase_scores" in temporal_accuracy:
            for phase_name, phase_data in temporal_accuracy["phase_scores"].items():
                score = phase_data.get("score", 0)
                duration = phase_data.get("duration", 0)
                target = phase_data.get("target", 0)
                deviation = phase_data.get("deviation", 0)
                
                if score >= 0.9:
                    timing_quality = "Elite temporal execution"
                elif score >= 0.8:
                    timing_quality = "Advanced timing coordination"
                elif score >= 0.7:
                    timing_quality = "Good timing with minor deviations"
                else:
                    timing_quality = "Significant timing issues requiring correction"
                
                assessment["phase_timing_analysis"][phase_name] = {
                    "timing_quality": timing_quality,
                    "actual_duration": duration,
                    "target_duration": target,
                    "deviation_seconds": deviation,
                    "timing_score": score
                }
        
        # Rhythm coordination assessment
        overall_score = assessment["overall_timing_score"]
        if overall_score >= 0.9:
            assessment["rhythm_coordination"] = "Olympic-level rhythm and coordination"
        elif overall_score >= 0.8:
            assessment["rhythm_coordination"] = "Advanced temporal coordination"
        elif overall_score >= 0.7:
            assessment["rhythm_coordination"] = "Good timing foundation with refinement needed"
        else:
            assessment["rhythm_coordination"] = "Fundamental timing coordination requires development"
        
        # Temporal efficiency
        assessment["temporal_efficiency"] = overall_score
        
        # Technique-specific timing recommendations
        assessment["timing_recommendations"] = self._generate_timing_recommendations(temporal_accuracy, technique)
        
        return assessment
    
    def _generate_position_feedback(self, analysis_results: dict, position: str) -> dict:
        """Generate position-specific feedback"""
        
        if position not in self.position_standards:
            return {"position": "unknown", "suitability": "not_assessed"}
        
        position_data = analysis_results.get("position_specific_metrics", {})
        suitability_score = position_data.get("suitability_score", 0)
        
        feedback = {
            "position": position,
            "suitability_score": suitability_score,
            "position_strengths": [],
            "position_weaknesses": [],
            "role_specific_recommendations": [],
            "movement_pattern_analysis": "",
            "positional_adaptation_needed": False
        }
        
        # Movement pattern analysis
        movement_pattern = position_data.get("movement_pattern", "")
        if suitability_score >= 0.85:
            feedback["movement_pattern_analysis"] = f"Excellent adaptation to {position} movement patterns"
        elif suitability_score >= 0.7:
            feedback["movement_pattern_analysis"] = f"Good foundation for {position} position with specific adaptations needed"
        else:
            feedback["movement_pattern_analysis"] = f"Significant adaptation required for optimal {position} performance"
            feedback["positional_adaptation_needed"] = True
        
        # Position-specific metrics analysis
        position_metrics = position_data.get("position_specific_metrics", {})
        for metric, data in position_metrics.items():
            if data.get("within_tolerance", False):
                feedback["position_strengths"].append(f"{metric.replace('_', ' ').title()}: {data['measured']:.1f}")
            else:
                feedback["position_weaknesses"].append(f"{metric.replace('_', ' ').title()}: {data['measured']:.1f} (target: {data['target']:.1f})")
        
        # Role-specific recommendations
        key_characteristics = position_data.get("key_characteristics", [])
        feedback["role_specific_recommendations"] = self._generate_position_recommendations(position, suitability_score, key_characteristics)
        
        return feedback
    
    def _generate_elite_corrections(self, elite_comparisons: dict, technique: str, position: str) -> List[dict]:
        """Generate elite-level corrections"""
        
        corrections = []
        improvement_areas = elite_comparisons.get("improvement_areas", [])
        metric_comparisons = elite_comparisons.get("metric_comparisons", {})
        
        for i, area in enumerate(improvement_areas[:3]):
            if area in metric_comparisons:
                comparison = metric_comparisons[area]
                deviation = comparison.get("deviation", 0)
                measured = comparison.get("measured", 0)
                target = comparison.get("target", 0)
                percentile = comparison.get("percentile", 0)
                
                correction = {
                    "metric": area,
                    "problem": self._identify_specific_problem(area, deviation, technique, position),
                    "feel_cue": get_elite_coaching_cue(technique, area),
                    "drill": self._prescribe_elite_drill(area, technique, position),
                    "prescription": self._create_elite_prescription(area, deviation, technique),
                    "why_it_works": self._explain_elite_mechanism(area, technique, position),
                    "deviation_analysis": f"Current: {measured:.1f}, Elite: {target:.1f}, Gap: {deviation:.1f} ({percentile:.0f}th percentile)"
                }
                
                corrections.append(correction)
        
        return corrections
    
    def _generate_training_prescription(self, analysis_results: dict, athlete_level: str, session_history: list) -> dict:
        """Generate Olympic-level training prescription"""
        
        olympic_readiness = analysis_results.get("olympic_readiness_score", 0)
        improvement_areas = analysis_results.get("elite_comparisons", {}).get("improvement_areas", [])
        temporal_accuracy = analysis_results.get("temporal_accuracy", {})
        
        prescription = {
            "training_phase": self._determine_training_phase(olympic_readiness, athlete_level),
            "weekly_structure": {},
            "specific_drills": [],
            "progression_milestones": [],
            "volume_intensity": {},
            "recovery_protocols": [],
            "periodization": ""
        }
        
        # Determine training phase
        if olympic_readiness >= 90:
            prescription["training_phase"] = "Elite Optimization"
            prescription["periodization"] = "Competition phase with technical refinement"
        elif olympic_readiness >= 80:
            prescription["training_phase"] = "Advanced Development"
            prescription["periodization"] = "Pre-competition phase with performance focus"
        elif olympic_readiness >= 70:
            prescription["training_phase"] = "Technical Foundation"
            prescription["periodization"] = "Preparation phase with technical emphasis"
        else:
            prescription["training_phase"] = "Fundamental Development"
            prescription["periodization"] = "Foundation phase with skill acquisition"
        
        # Weekly structure based on level and readiness
        prescription["weekly_structure"] = self._create_weekly_structure(olympic_readiness, athlete_level, improvement_areas)
        
        # Specific drills
        technique = analysis_results.get("technique", "unknown")
        prescription["specific_drills"] = self._prescribe_elite_drills(improvement_areas, technique, olympic_readiness)
        
        # Progression milestones
        prescription["progression_milestones"] = self._create_progression_milestones(olympic_readiness, improvement_areas)
        
        # Volume and intensity
        prescription["volume_intensity"] = self._determine_volume_intensity(olympic_readiness, athlete_level)
        
        # Recovery protocols
        prescription["recovery_protocols"] = self._prescribe_recovery_protocols(olympic_readiness, session_history)
        
        return prescription
    
    def _generate_performance_projection(self, analysis_results: dict, athlete_level: str) -> dict:
        """Generate performance projection based on current analysis"""
        
        olympic_readiness = analysis_results.get("olympic_readiness_score", 0)
        improvement_areas = analysis_results.get("elite_comparisons", {}).get("improvement_areas", [])
        
        projection = {
            "current_level": athlete_level,
            "projected_timeline": {},
            "performance_ceiling": "",
            "critical_success_factors": [],
            "potential_barriers": [],
            "optimization_priorities": []
        }
        
        # Projected timeline
        if olympic_readiness >= 90:
            projection["projected_timeline"] = {
                "4_weeks": "Maintain elite level with minor refinements",
                "8_weeks": "Peak performance for major competition",
                "12_weeks": "Sustained elite performance through season"
            }
            projection["performance_ceiling"] = "Olympic medal contender"
        elif olympic_readiness >= 80:
            projection["projected_timeline"] = {
                "4_weeks": "Achieve elite-level consistency",
                "8_weeks": "Compete at international level",
                "12_weeks": "Olympic qualification standard"
            }
            projection["performance_ceiling"] = "International competitor"
        elif olympic_readiness >= 70:
            projection["projected_timeline"] = {
                "4_weeks": "Advanced level with improved consistency",
                "8_weeks": "National team consideration",
                "12_weeks": "International competition ready"
            }
            projection["performance_ceiling"] = "National team level"
        else:
            projection["projected_timeline"] = {
                "4_weeks": "Solid technical foundation",
                "8_weeks": "Advanced level achievement",
                "12_weeks": "Elite development track"
            }
            projection["performance_ceiling"] = "Advanced club level"
        
        # Critical success factors
        projection["critical_success_factors"] = self._identify_success_factors(analysis_results)
        
        # Potential barriers
        projection["potential_barriers"] = self._identify_potential_barriers(analysis_results)
        
        # Optimization priorities
        projection["optimization_priorities"] = improvement_areas[:3] if improvement_areas else ["overall_technique"]
        
        return projection
    
    def _determine_next_focus(self, analysis_results: dict, session_history: list) -> str:
        """Determine the most important focus for next session"""
        
        improvement_areas = analysis_results.get("elite_comparisons", {}).get("improvement_areas", [])
        critical_violations = analysis_results.get("elite_comparisons", {}).get("critical_violations", [])
        temporal_accuracy = analysis_results.get("temporal_accuracy", {})
        
        # Prioritize critical violations first
        if critical_violations:
            return f"CRITICAL: Address {critical_violations[0]} - this is limiting your elite potential"
        
        # Then prioritize temporal issues
        if temporal_accuracy and temporal_accuracy.get("overall_timing_score", 0) < 0.8:
            return "Focus on movement rhythm and phase timing coordination"
        
        # Then work on biomechanical improvements
        if improvement_areas:
            return f"Refine {improvement_areas[0].replace('_', ' ')} technique for elite-level execution"
        
        # Default to consistency
        return "Maintain current technique while building consistency under pressure"
    
    def _generate_injury_prevention(self, analysis_results: dict, technique: str, position: str) -> List[str]:
        """Generate injury prevention recommendations"""
        
        elite_comparisons = analysis_results.get("elite_comparisons", {}).get("metric_comparisons", {})
        
        injury_recommendations = []
        
        # Technique-specific injury risks
        if technique == "spike":
            # Check for shoulder-related issues
            shoulder_metrics = [m for m in elite_comparisons.keys() if "shoulder" in m or "elbow" in m]
            for metric in shoulder_metrics:
                comparison = elite_comparisons[metric]
                if not comparison.get("is_elite", False) and abs(comparison.get("deviation", 0)) > 10:
                    injury_recommendations.append(f"Shoulder injury risk: Address {metric} to prevent overuse injuries")
            
            # Landing-related risks
            if "landing_balance" in elite_comparisons:
                landing_comp = elite_comparisons["landing_balance"]
                if landing_comp.get("performance_score", 0) < 0.7:
                    injury_recommendations.append("Landing technique needs improvement to prevent knee/ankle injuries")
        
        elif technique == "block":
            # Finger/wrist injury prevention
            injury_recommendations.extend([
                "Ensure proper finger positioning to prevent jamming",
                "Strengthen wrist muscles for repetitive blocking",
                "Focus on landing technique to prevent lower body injuries"
            ])
        
        # Position-specific injury patterns
        if position == "middle":
            injury_recommendations.extend([
                "High block volume requires shoulder strengthening program",
                "Repetitive jumping demands proper landing mechanics",
                "Quick lateral movements need hip flexibility maintenance"
            ])
        
        # General injury prevention
        injury_recommendations.extend([
            "Implement comprehensive warm-up routine before practice",
            "Include shoulder stability exercises in training program",
            "Maintain flexibility through regular stretching",
            "Progress training volume gradually to prevent overuse"
        ])
        
        return injury_recommendations
    
    def _assess_competition_readiness(self, analysis_results: dict, tournament_context: str) -> dict:
        """Assess readiness for specific competition level"""
        
        olympic_readiness = analysis_results.get("olympic_readiness_score", 0)
        elite_comparisons = analysis_results.get("elite_comparisons", {})
        critical_violations = elite_comparisons.get("critical_violations", [])
        
        readiness = {
            "current_readiness_level": "",
            "competition_specific_assessment": "",
            "readiness_timeline": "",
            "confidence_level": 0,
            "preparation_priorities": []
        }
        
        # Determine readiness level based on context
        if tournament_context == "olympic_games":
            if olympic_readiness >= 90 and not critical_violations:
                readiness["current_readiness_level"] = "OLYMPIC READY"
                readiness["competition_specific_assessment"] = "Technique meets Olympic standards"
                readiness["readiness_timeline"] = "Competition ready now"
                readiness["confidence_level"] = 95
            elif olympic_readiness >= 85:
                readiness["current_readiness_level"] = "OLYMPIC COMPETITIVE"
                readiness["competition_specific_assessment"] = "Competitive at Olympic level with minor refinements"
                readiness["readiness_timeline"] = "Ready with 2-4 weeks specific preparation"
                readiness["confidence_level"] = 80
            else:
                readiness["current_readiness_level"] = "OLYMPIC DEVELOPMENT"
                readiness["competition_specific_assessment"] = "Requires significant development for Olympic competition"
                readiness["readiness_timeline"] = "6-12 months intensive preparation needed"
                readiness["confidence_level"] = 40
        
        elif tournament_context == "world_championship":
            if olympic_readiness >= 80:
                readiness["current_readiness_level"] = "WORLD CHAMPIONSHIP READY"
                readiness["confidence_level"] = 85
                readiness["readiness_timeline"] = "Ready for world-level competition"
            else:
                readiness["current_readiness_level"] = "CHAMPIONSHIP DEVELOPMENT"
                readiness["confidence_level"] = 60
                readiness["readiness_timeline"] = "3-6 months preparation for championship level"
        
        else:  # Training/club level
            if olympic_readiness >= 70:
                readiness["current_readiness_level"] = "ADVANCED CLUB READY"
                readiness["confidence_level"] = 90
                readiness["readiness_timeline"] = "Ready for high-level club competition"
            else:
                readiness["current_readiness_level"] = "DEVELOPMENTAL"
                readiness["confidence_level"] = 70
                readiness["readiness_timeline"] = "Continue technical development"
        
        # Preparation priorities
        if critical_violations:
            readiness["preparation_priorities"] = [f"Address critical: {violations[:1]}" for violations in critical_violations]
        else:
            readiness["preparation_priorities"] = ["Maintain current technique", "Build competition experience", "Develop mental toughness"]
        
        return readiness
    
    # Helper methods for specific analyses
    def _get_strength_description(self, metric: str, technique: str) -> str:
        """Get description of technical strength"""
        strength_descriptions = {
            "spike": {
                "elbow_flexion_impact": "Excellent arm extension at contact - generating maximum power",
                "jump_height": "Superior vertical leap - creating optimal attack angle",
                "approach_speed": "Efficient approach timing - maximizing momentum conversion",
                "torso_extension": "Optimal body positioning for power generation",
                "spike_speed": "Elite-level ball velocity - difficult to defend"
            },
            "block": {
                "hand_position_height": "Excellent penetration over the net",
                "reaction_time": "Quick read and react capability",
                "shoulder_width_ratio": "Optimal blocking position coverage",
                "landing_balance": "Stable landing technique preventing injuries"
            },
            "serve": {
                "toss_height": "Consistent toss placement for optimal contact",
                "shoulder_rotation": "Effective shoulder rotation for power generation",
                "contact_point_height": "High contact point creating difficult angles"
            },
            "dig": {
                "platform_angle": "Optimal forearm platform for ball control",
                "knee_bend_angle": "Proper low position for effective digging",
                "recovery_position": "Quick return to ready position"
            }
        }
        
        return strength_descriptions.get(technique, {}).get(metric, f"Strong {metric.replace('_', ' ')}")
    
    def _get_weakness_description(self, metric: str, technique: str) -> str:
        """Get description of technical weakness"""
        weakness_descriptions = {
            "spike": {
                "elbow_flexion_impact": "Limited arm extension reducing power output",
                "jump_height": "Suboptimal vertical leap affecting attack angle",
                "approach_speed": "Inefficient approach timing limiting momentum",
                "torso_extension": "Poor body positioning reducing power transfer",
                "spike_speed": "Below-elite ball velocity easier to defend"
            },
            "block": {
                "hand_position_height": "Insufficient penetration over the net",
                "reaction_time": "Slow read and react timing",
                "shoulder_width_ratio": "Limited blocking coverage area",
                "landing_balance": "Unstable landing technique"
            },
            "serve": {
                "toss_height": "Inconsistent toss affecting contact quality",
                "shoulder_rotation": "Limited shoulder rotation reducing power",
                "contact_point_height": "Low contact point creating predictable serves"
            },
            "dig": {
                "platform_angle": "Suboptimal forearm platform reducing control",
                "knee_bend_angle": "High position limiting digging effectiveness",
                "recovery_position": "Slow return to ready position"
            }
        }
        
        return weakness_descriptions.get(technique, {}).get(metric, f"Needs improvement in {metric.replace('_', ' ')}")
    
    def _get_biomechanical_implication(self, metric: str, deviation: float, technique: str) -> str:
        """Get biomechanical implication of deviation"""
        implications = {
            "spike": {
                "elbow_flexion_impact": f"{abs(deviation):.1f}° deviation reduces power transfer efficiency by {abs(deviation)*0.5:.1f}%",
                "jump_height": f"{abs(deviation):.1f}m deviation affects attack angle and defensive reading",
                "approach_speed": f"{abs(deviation):.1f}m/s deviation limits momentum conversion to vertical lift"
            },
            "block": {
                "hip_angle": f"{abs(deviation):.1f}° deviation reduces blocking stability and penetration",
                "reaction_time": f"{abs(deviation):.2f}s deviation significantly affects block timing success"
            }
        }
        
        return implications.get(technique, {}).get(metric, f"Biomechanical deviation of {abs(deviation):.1f} affects technique efficiency")
    
    def _identify_specific_problem(self, metric: str, deviation: float, technique: str, position: str) -> str:
        """Identify specific technical problem"""
        
        if technique == "spike" and metric == "elbow_flexion_impact":
            if deviation < 0:
                return "Early arm extension reducing whip-like power generation"
            else:
                return "Late arm extension limiting follow-through power"
        
        elif technique == "block" and metric == "hip_angle":
            if deviation > 0:
                return "Insufficient hip drop reducing blocking stability and penetration"
            else:
                return "Excessive hip drop affecting quick recovery"
        
        return f"Suboptimal {metric.replace('_', ' ')} execution affecting {technique} technique efficiency"
    
    def _prescribe_elite_drill(self, metric: str, technique: str, position: str) -> str:
        """Prescribe specific elite-level drill"""
        
        elite_drills = {
            "spike": {
                "elbow_flexion_impact": "Wall shadow drill with freeze at contact",
                "jump_height": "Depth jump to spike approach progression",
                "approach_speed": "Metronome-paced approach timing drill"
            },
            "block": {
                "hip_angle": "Wall sit progression with blocking arm movements",
                "reaction_time": "Random cue reaction and jump drill"
            }
        }
        
        return elite_drills.get(technique, {}).get(metric, f"Elite {technique} {metric.replace('_', ' ')} drill")
    
    def _create_elite_prescription(self, metric: str, deviation: float, technique: str) -> str:
        """Create specific training prescription"""
        
        if abs(deviation) <= 5:
            return "3 sets of 15 reps, focus on feel and consistency"
        elif abs(deviation) <= 10:
            return "4 sets of 12 reps, emphasize technical correction"
        else:
            return "5 sets of 10 reps, fundamental technique reconstruction"
    
    def _explain_elite_mechanism(self, metric: str, technique: str, position: str) -> str:
        """Explain why the correction works"""
        
        mechanisms = {
            "spike": {
                "elbow_flexion_impact": "Optimal elbow extension timing maximizes kinetic chain energy transfer",
                "jump_height": "Higher contact point creates steeper attack angles and reduces defensive reaction time"
            },
            "block": {
                "hip_angle": "Proper hip angle creates stable base for explosive upward movement and net penetration"
            }
        }
        
        return mechanisms.get(technique, {}).get(metric, "Corrects biomechanical inefficiency for optimal performance")
    
    def _identify_power_metrics(self, technique: str) -> List[str]:
        """Identify metrics related to power generation"""
        power_metrics = {
            "spike": ["elbow_flexion_impact", "jump_height", "spike_speed", "torso_extension_initial"],
            "block": ["jump_height", "hand_position_height", "reaction_time"],
            "serve": ["shoulder_rotation", "contact_point_height", "toss_height"],
            "dig": ["platform_angle", "knee_bend_angle"]
        }
        return power_metrics.get(technique, [])
    
    def _identify_sequence_metrics(self, technique: str) -> List[str]:
        """Identify metrics related to movement sequence"""
        sequence_metrics = {
            "spike": ["approach_speed", "leg_flexion_repulsion", "elbow_flexion_repulsion"],
            "block": ["reaction_time", "penultimate_step"],
            "serve": ["step_timing", "body_lean_angle"],
            "dig": ["reception_window", "recovery_time"]
        }
        return sequence_metrics.get(technique, [])
    
    def _assess_injury_risk(self, metric_comparisons: dict, technique: str) -> str:
        """Assess injury risk based on biomechanical deviations"""
        
        high_risk_metrics = []
        for metric, comparison in metric_comparisons.items():
            if not comparison.get("is_elite", False) and abs(comparison.get("deviation", 0)) > 15:
                high_risk_metrics.append(metric)
        
        if not high_risk_metrics:
            return "Low injury risk - technique within safe biomechanical parameters"
        elif len(high_risk_metrics) <= 2:
            return f"Moderate injury risk - address {', '.join(high_risk_metrics[:2])} to prevent overuse injuries"
        else:
            return "High injury risk - comprehensive technique correction needed to prevent injury"
    
    def _generate_biomechanical_recommendations(self, metric_comparisons: dict, technique: str, position: str) -> List[str]:
        """Generate biomechanical improvement recommendations"""
        
        recommendations = []
        
        for metric, comparison in metric_comparisons.items():
            if not comparison.get("is_elite", False):
                deviation = comparison.get("deviation", 0)
                percentile = comparison.get("percentile", 0)
                
                if percentile < 70:
                    recommendations.append(f"Priority: Correct {metric.replace('_', ' ')} - currently {percentile:.0f}th percentile")
                elif percentile < 85:
                    recommendations.append(f"Refine: Improve {metric.replace('_', ' ')} for elite-level execution")
        
        return recommendations[:3]  # Limit to top 3 recommendations
    
    def _generate_timing_recommendations(self, temporal_accuracy: dict, technique: str) -> List[str]:
        """Generate timing-specific recommendations"""
        
        recommendations = []
        overall_score = temporal_accuracy.get("overall_timing_score", 0)
        
        if overall_score < 0.7:
            recommendations.append("Fundamental timing coordination requires systematic development")
            recommendations.append("Use metronome training to establish consistent rhythm")
        elif overall_score < 0.85:
            recommendations.append("Refine phase transitions for smoother movement flow")
            recommendations.append("Practice with video feedback to optimize timing")
        else:
            recommendations.append("Maintain current timing while building consistency")
        
        # Technique-specific timing recommendations
        if technique == "spike":
            recommendations.append("Focus on 4-step approach rhythm: slow-fast-fast-contact")
        elif technique == "block":
            recommendations.append("Train reaction timing with random visual cues")
        elif technique == "serve":
            recommendations.append("Establish consistent toss-to-contact timing")
        elif technique == "dig":
            recommendations.append("Practice reception within 0.7-second window for jump serves")
        
        return recommendations
    
    def _determine_training_phase(self, olympic_readiness: float, athlete_level: str) -> str:
        """Determine appropriate training phase"""
        
        if olympic_readiness >= 90:
            return "Elite Optimization Phase"
        elif olympic_readiness >= 80:
            return "Advanced Development Phase"
        elif olympic_readiness >= 70:
            return "Technical Foundation Phase"
        else:
            return "Fundamental Development Phase"
    
    def _create_weekly_structure(self, olympic_readiness: float, athlete_level: str, improvement_areas: list) -> dict:
        """Create weekly training structure"""
        
        if olympic_readiness >= 90:
            return {
                "technical_sessions": 3,
                "physical_sessions": 2,
                "competition_simulation": 1,
                "recovery_sessions": 1,
                "total_training_hours": 20
            }
        elif olympic_readiness >= 80:
            return {
                "technical_sessions": 4,
                "physical_sessions": 2,
                "competition_simulation": 1,
                "recovery_sessions": 1,
                "total_training_hours": 18
            }
        else:
            return {
                "technical_sessions": 3,
                "physical_sessions": 2,
                "competition_simulation": 0,
                "recovery_sessions": 1,
                "total_training_hours": 12
            }
    
    def _prescribe_elite_drills(self, improvement_areas: list, technique: str, olympic_readiness: float) -> List[str]:
        """Prescribe elite-level drills"""
        
        drills = []
        
        for area in improvement_areas[:3]:
            if technique == "spike":
                if "elbow" in area:
                    drills.append("Wall shadow drill with contact freeze - 3x15 reps")
                elif "jump" in area:
                    drills.append("Depth jump to approach progression - 4x8 reps")
                elif "approach" in area:
                    drills.append("Metronome-paced approach timing - 5x6 reps")
            
            elif technique == "block":
                if "reaction" in area:
                    drills.append("Random cue reaction jumps - 4x10 reps")
                elif "hip" in area:
                    drills.append("Wall sit with blocking arms - 3x30 second holds")
                elif "penetration" in area:
                    drills.append("Net penetration holds - 3x12 reps")
        
        return drills
    
    def _create_progression_milestones(self, olympic_readiness: float, improvement_areas: list) -> List[dict]:
        """Create progression milestones"""
        
        milestones = []
        
        if olympic_readiness >= 90:
            milestones = [
                {"week": 2, "target": "Maintain elite consistency in all metrics"},
                {"week": 4, "target": "Achieve 95th percentile performance across all areas"},
                {"week": 8, "target": "Peak performance for major competition"}
            ]
        elif olympic_readiness >= 80:
            milestones = [
                {"week": 2, "target": "Achieve elite level in top 2 improvement areas"},
                {"week": 4, "target": "Reach 90th percentile overall performance"},
                {"week": 8, "target": "Consistent elite-level execution"}
            ]
        else:
            milestones = [
                {"week": 2, "target": "Correct fundamental technique errors"},
                {"week": 4, "target": "Achieve 80th percentile performance"},
                {"week": 8, "target": "Advanced level consistency"}
            ]
        
        return milestones
    
    def _determine_volume_intensity(self, olympic_readiness: float, athlete_level: str) -> dict:
        """Determine training volume and intensity"""
        
        if olympic_readiness >= 90:
            return {
                "intensity": "Maximum (90-95% effort)",
                "volume": "High (20+ hours/week)",
                "frequency": "Daily with active recovery",
                "load_management": "Periodized with competition schedule"
            }
        elif olympic_readiness >= 80:
            return {
                "intensity": "High (85-90% effort)",
                "volume": "Moderate-High (15-20 hours/week)",
                "frequency": "6 days/week with 1 rest day",
                "load_management": "Progressive overload with deload weeks"
            }
        else:
            return {
                "intensity": "Moderate-High (75-85% effort)",
                "volume": "Moderate (10-15 hours/week)",
                "frequency": "5-6 days/week with rest days",
                "load_management": "Gradual progression with technique focus"
            }
    
    def _prescribe_recovery_protocols(self, olympic_readiness: float, session_history: list) -> List[str]:
        """Prescribe recovery protocols"""
        
        protocols = []
        
        if olympic_readiness >= 90:
            protocols.extend([
                "Daily sports massage and physiotherapy",
                "Advanced recovery technology (cryotherapy, compression)",
                "Sleep optimization protocol (8+ hours nightly)",
                "Nutrition periodization with competition schedule"
            ])
        elif olympic_readiness >= 80:
            protocols.extend([
                "Regular sports massage (2-3x/week)",
                "Ice bath protocol after high-intensity sessions",
                "Sleep hygiene optimization (7-8 hours)",
                "Anti-inflammatory nutrition focus"
            ])
        else:
            protocols.extend([
                "Basic stretching and foam rolling routine",
                "Adequate sleep (7+ hours nightly)",
                "Hydration and nutrition focus",
                "Rest day activities for active recovery"
            ])
        
        # Add session-specific recovery based on history
        if session_history and len(session_history) > 3:
            recent_sessions = session_history[-3:]
            if any(session.get("intensity", 0) > 8 for session in recent_sessions):
                protocols.append("Extra recovery focus after high-intensity sessions")
        
        return protocols
    
    def _generate_position_recommendations(self, position: str, suitability_score: float, key_characteristics: list) -> List[str]:
        """Generate position-specific recommendations"""
        
        recommendations = []
        
        if suitability_score < 0.7:
            recommendations.extend([
                f"Focus on fundamental {position} movement patterns",
                f"Develop {', '.join(key_characteristics[:2])} through specific drills",
                f"Study elite {position} players for movement pattern modeling"
            ])
        elif suitability_score < 0.85:
            recommendations.extend([
                f"Refine {position}-specific techniques for optimal performance",
                f"Enhance {key_characteristics[0]} through targeted training",
                f"Practice position-specific scenarios and decision-making"
            ])
        else:
            recommendations.extend([
                f"Maintain excellence in {position} movement patterns",
                f"Continue developing advanced {position} techniques",
                f"Focus on consistency and pressure performance"
            ])
        
        return recommendations
    
    def _identify_success_factors(self, analysis_results: dict) -> List[str]:
        """Identify critical success factors"""
        
        factors = []
        strengths = analysis_results.get("elite_comparisons", {}).get("strengths", [])
        olympic_readiness = analysis_results.get("olympic_readiness_score", 0)
        
        if olympic_readiness >= 80:
            factors.extend([
                "Strong technical foundation to build upon",
                "Demonstrated ability to perform at advanced levels",
                "Solid biomechanical efficiency"
            ])
        
        if strengths:
            factors.append(f"Natural strength in {strengths[0].replace('_', ' ')} provides competitive advantage")
        
        factors.extend([
            "Access to Olympic-level coaching and analysis",
            "Systematic approach to technique development",
            "Data-driven feedback for continuous improvement"
        ])
        
        return factors
    
    def _identify_potential_barriers(self, analysis_results: dict) -> List[str]:
        """Identify potential performance barriers"""
        
        barriers = []
        improvement_areas = analysis_results.get("elite_comparisons", {}).get("improvement_areas", [])
        critical_violations = analysis_results.get("elite_comparisons", {}).get("critical_violations", [])
        
        if critical_violations:
            barriers.append("Critical technique violations must be addressed immediately")
        
        if len(improvement_areas) > 3:
            barriers.append("Multiple improvement areas may slow progression rate")
        
        barriers.extend([
            "Time required for biomechanical adaptation",
            "Need for consistent high-quality practice",
            "Physical conditioning requirements for elite level",
            "Mental preparation for high-pressure competition"
        ])
        
        return barriers

# Create global instance
elite_coaching_engine = EliteCoachingEngine()

def generate_elite_coaching_feedback(analysis_results: dict, athlete_level: str = "intermediate", 
                                     session_history: list = None, tournament_context: str = "training") -> dict:
    """Generate Olympic-level coaching feedback"""
    return elite_coaching_engine.generate_elite_feedback(analysis_results, athlete_level, session_history, tournament_context)
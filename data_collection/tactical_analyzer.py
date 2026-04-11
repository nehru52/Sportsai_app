"""
Tactical Layer Integration for Volleyball Analysis
Parses Data Volley (.dvw) files and integrates with biomechanical analysis
Connects tactical context (set tempo, attack zones) with joint kinematics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import re
from datetime import datetime, timedelta

@dataclass
class TacticalAction:
    timestamp: float
    action_type: str
    player_id: str
    zone: int
    tempo: str
    quality: int
    rally_sequence: List[str]
    technical_details: Dict[str, any]

@dataclass
class RallyContext:
    rally_id: int
    start_time: float
    end_time: float
    serve_type: str
    reception_quality: int
    set_tempo: str
    attack_zone: int
    attack_result: str
    players_involved: List[str]

class DataVolleyParser:
    """Parse Data Volley (.dvw) files for tactical analysis"""
    
    def __init__(self):
        # Data Volley action codes mapping
        self.action_codes = {
            'S': 'serve', 'A': 'attack', 'B': 'block', 'R': 'reception', 
            'P': 'set', 'D': 'dig', 'E': 'error', '#': 'point'
        }
        
        # Set tempo classifications
        self.tempo_mapping = {
            '1': 'first_tempo',      # Quick sets (1s)
            '2': 'second_tempo',     # Medium tempo (2s) 
            '3': 'high_ball',        # High ball (3s+)
            'H': 'hut',              # Hut (fast to outside)
            'G': 'go',               # Go (fast to opposite)
            'C': 'chaos'             # Chaos (variable)
        }
        
        # Attack zones (1-9 for Data Volley)
        self.attack_zones = {
            1: 'back_left', 2: 'back_center', 3: 'back_right',
            4: 'front_left', 5: 'front_center', 6: 'front_right',
            7: 'pipe', 8: 'back_row_right', 9: 'back_row_left'
        }
        
        # Quality scale (1-3 for Data Volley)
        self.quality_scale = {
            1: 'poor', 2: 'average', 3: 'excellent'
        }
    
    def parse_dvw_file(self, file_path: str) -> pd.DataFrame:
        """Parse Data Volley file and return structured data"""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # Parse Data Volley format
            rallies = []
            current_rally = []
            rally_start_time = 0.0
            
            for line_num, line in enumerate(lines):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse rally data
                if line.startswith('RALLY'):
                    # New rally starts
                    if current_rally:
                        rallies.extend(self.parse_rally(current_rally, rally_start_time))
                    
                    current_rally = [line]
                    # Extract rally start time from RALLY line
                    time_match = re.search(r'TIME:([\d.]+)', line)
                    rally_start_time = float(time_match.group(1)) if time_match else 0.0
                
                else:
                    current_rally.append(line)
            
            # Parse final rally
            if current_rally:
                rallies.extend(self.parse_rally(current_rally, rally_start_time))
            
            # Convert to DataFrame
            df = pd.DataFrame(rallies)
            return df
            
        except Exception as e:
            print(f"[TacticalParser] Error parsing .dvw file: {e}")
            return pd.DataFrame()
    
    def parse_rally(self, rally_lines: List[str], rally_start_time: float) -> List[Dict]:
        """Parse individual rally data"""
        
        actions = []
        rally_time_offset = 0.0
        
        for line in rally_lines:
            # Parse action line format: TIME ACTION PLAYER ZONE TEMPO QUALITY
            parts = line.split()
            if len(parts) < 4:
                continue
            
            try:
                # Extract components
                time_offset = float(parts[0]) if parts[0].replace('.', '').isdigit() else rally_time_offset
                action_code = parts[1] if parts[1] in self.action_codes else 'E'
                player_id = parts[2] if len(parts) > 2 else 'unknown'
                zone = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                tempo = parts[4] if len(parts) > 4 and parts[4] in self.tempo_mapping else '3'
                quality = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 2
                
                action_data = {
                    'timestamp': rally_start_time + time_offset,
                    'action_type': self.action_codes.get(action_code, 'error'),
                    'player_id': player_id,
                    'zone': zone,
                    'tempo': self.tempo_mapping.get(tempo, 'high_ball'),
                    'quality': quality,
                    'raw_code': action_code,
                    'rally_sequence': self.build_rally_sequence(rally_lines)
                }
                
                actions.append(action_data)
                rally_time_offset = time_offset
                
            except (ValueError, IndexError) as e:
                print(f"[TacticalParser] Error parsing rally line: {line} - {e}")
                continue
        
        return actions
    
    def build_rally_sequence(self, rally_lines: List[str]) -> List[str]:
        """Build sequence of actions in rally"""
        
        sequence = []
        for line in rally_lines:
            if not line.startswith('RALLY'):
                parts = line.split()
                if parts and parts[0].replace('.', '').isdigit():
                    action_code = parts[1] if len(parts) > 1 else 'E'
                    sequence.append(self.action_codes.get(action_code, 'error'))
        
        return sequence

class TacticalAnalyzer:
    """Main tactical analysis engine integrating Data Volley data"""
    
    def __init__(self):
        self.parser = DataVolleyParser()
        self.rally_contexts = []
        self.tactical_patterns = {}
        
        # Load tactical benchmarks
        self.load_tactical_benchmarks()
    
    def load_tactical_benchmarks(self):
        """Load tactical benchmarks from FIVB data"""
        
        self.tactical_benchmarks = {
            'serve': {
                'zones': {1: 0.15, 6: 0.25, 5: 0.20, 2: 0.15, 3: 0.10, 4: 0.15},
                'tempo_distribution': {'float': 0.4, 'jump': 0.6},
                'ace_rate': 0.08,
                'error_rate': 0.12
            },
            'attack': {
                'tempo_distribution': {'first_tempo': 0.25, 'second_tempo': 0.45, 'high_ball': 0.30},
                'zone_distribution': {4: 0.35, 2: 0.25, 6: 0.20, 1: 0.10, 5: 0.05, 3: 0.05},
                'kill_rate': 0.45,
                'error_rate': 0.18
            },
            'reception': {
                'quality_distribution': {3: 0.25, 2: 0.45, 1: 0.30},
                'perfect_pass_rate': 0.25,
                'error_rate': 0.08
            },
            'set': {
                'tempo_accuracy': {'first_tempo': 0.75, 'second_tempo': 0.85, 'high_ball': 0.95},
                'zone_accuracy': 0.82
            }
        }
    
    def analyze_match(self, dvw_file_path: str, video_path: Optional[str] = None) -> Dict:
        """Complete tactical analysis of volleyball match"""
        
        print(f"[TacticalAnalyzer] Analyzing match: {dvw_file_path}")
        
        # Parse Data Volley file
        tactical_data = self.parser.parse_dvw_file(dvw_file_path)
        
        if tactical_data.empty:
            print("[TacticalAnalyzer] No tactical data found")
            return {}
        
        # Build rally contexts
        rally_contexts = self.build_rally_contexts(tactical_data)
        
        # Analyze tactical patterns
        patterns = self.analyze_tactical_patterns(tactical_data)
        
        # Generate tactical insights
        insights = self.generate_tactical_insights(tactical_data, patterns)
        
        # Create comprehensive analysis
        analysis = {
            'match_summary': self.generate_match_summary(tactical_data),
            'rally_analysis': rally_contexts,
            'tactical_patterns': patterns,
            'performance_benchmarks': self.compare_to_benchmarks(tactical_data),
            'tactical_insights': insights,
            'recommendations': self.generate_recommendations(tactical_data, patterns)
        }
        
        print(f"[TacticalAnalyzer] Analysis complete: {len(rally_contexts)} rallies analyzed")
        
        return analysis
    
    def build_rally_contexts(self, tactical_data: pd.DataFrame) -> List[RallyContext]:
        """Build detailed rally contexts for biomechanical integration"""
        
        contexts = []
        rally_groups = tactical_data.groupby(tactical_data['timestamp'].diff().gt(10).cumsum())
        
        for rally_id, rally_data in rally_groups:
            if len(rally_data) < 3:  # Skip very short rallies
                continue
            
            # Extract rally phases
            serve_action = rally_data[rally_data['action_type'] == 'serve'].iloc[0] if len(rally_data[rally_data['action_type'] == 'serve']) > 0 else None
            reception_action = rally_data[rally_data['action_type'] == 'reception'].iloc[0] if len(rally_data[rally_data['action_type'] == 'reception']) > 0 else None
            set_action = rally_data[rally_data['action_type'] == 'set'].iloc[0] if len(rally_data[rally_data['action_type'] == 'set']) > 0 else None
            attack_action = rally_data[rally_data['action_type'] == 'attack'].iloc[0] if len(rally_data[rally_data['action_type'] == 'attack']) > 0 else None
            
            # Determine rally outcome
            last_action = rally_data.iloc[-1]
            rally_result = 'point' if last_action['raw_code'] == '#' else 'continuation'
            
            context = RallyContext(
                rally_id=rally_id,
                start_time=rally_data['timestamp'].min(),
                end_time=rally_data['timestamp'].max(),
                serve_type=serve_action['tempo'] if serve_action is not None else 'unknown',
                reception_quality=reception_action['quality'] if reception_action is not None else 2,
                set_tempo=set_action['tempo'] if set_action is not None else 'high_ball',
                attack_zone=attack_action['zone'] if attack_action is not None else 0,
                attack_result=rally_result,
                players_involved=rally_data['player_id'].unique().tolist()
            )
            
            contexts.append(context)
        
        return contexts
    
    def analyze_tactical_patterns(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze tactical patterns in the match"""
        
        patterns = {}
        
        # Serve patterns
        serve_patterns = self.analyze_serve_patterns(tactical_data)
        patterns['serve'] = serve_patterns
        
        # Attack patterns  
        attack_patterns = self.analyze_attack_patterns(tactical_data)
        patterns['attack'] = attack_patterns
        
        # Reception patterns
        reception_patterns = self.analyze_reception_patterns(tactical_data)
        patterns['reception'] = reception_patterns
        
        # Transition patterns
        transition_patterns = self.analyze_transition_patterns(tactical_data)
        patterns['transition'] = transition_patterns
        
        return patterns
    
    def analyze_serve_patterns(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze serve tactical patterns"""
        
        serve_data = tactical_data[tactical_data['action_type'] == 'serve']
        
        if serve_data.empty:
            return {}
        
        patterns = {
            'zone_distribution': serve_data['zone'].value_counts().to_dict(),
            'tempo_distribution': serve_data['tempo'].value_counts().to_dict(),
            'quality_distribution': serve_data['quality'].value_counts().to_dict(),
            'player_preferences': serve_data.groupby('player_id')['zone'].apply(list).to_dict(),
            'effectiveness_by_zone': serve_data.groupby('zone')['quality'].mean().to_dict(),
            'sequence_patterns': self.extract_serve_sequences(tactical_data)
        }
        
        return patterns
    
    def analyze_attack_patterns(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze attack tactical patterns"""
        
        attack_data = tactical_data[tactical_data['action_type'] == 'attack']
        
        if attack_data.empty:
            return {}
        
        patterns = {
            'zone_distribution': attack_data['zone'].value_counts().to_dict(),
            'tempo_distribution': attack_data['tempo'].value_counts().to_dict(),
            'quality_distribution': attack_data['quality'].value_counts().to_dict(),
            'player_preferences': attack_data.groupby('player_id')['zone'].apply(list).to_dict(),
            'tempo_effectiveness': attack_data.groupby('tempo')['quality'].mean().to_dict(),
            'zone_effectiveness': attack_data.groupby('zone')['quality'].mean().to_dict(),
            'transition_patterns': self.extract_attack_transitions(tactical_data)
        }
        
        return patterns
    
    def analyze_reception_patterns(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze reception tactical patterns"""
        
        reception_data = tactical_data[tactical_data['action_type'] == 'reception']
        
        if reception_data.empty:
            return {}
        
        patterns = {
            'quality_distribution': reception_data['quality'].value_counts().to_dict(),
            'player_performance': reception_data.groupby('player_id')['quality'].mean().to_dict(),
            'serve_type_effectiveness': self.analyze_reception_vs_serve(tactical_data),
            'formation_analysis': self.analyze_reception_formation(tactical_data)
        }
        
        return patterns
    
    def analyze_transition_patterns(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze transition from defense to offense"""
        
        transitions = []
        
        # Find dig-to-attack transitions
        for i in range(len(tactical_data) - 1):
            current = tactical_data.iloc[i]
            next_action = tactical_data.iloc[i + 1]
            
            if current['action_type'] == 'dig' and next_action['action_type'] == 'set':
                transition_time = next_action['timestamp'] - current['timestamp']
                transitions.append({
                    'transition_time': transition_time,
                    'dig_quality': current['quality'],
                    'set_tempo': next_action['tempo'],
                    'transition_type': 'dig_to_set'
                })
        
        # Find reception-to-set transitions
        for i in range(len(tactical_data) - 1):
            current = tactical_data.iloc[i]
            next_action = tactical_data.iloc[i + 1]
            
            if current['action_type'] == 'reception' and next_action['action_type'] == 'set':
                transition_time = next_action['timestamp'] - current['timestamp']
                transitions.append({
                    'transition_time': transition_time,
                    'reception_quality': current['quality'],
                    'set_tempo': next_action['tempo'],
                    'transition_type': 'reception_to_set'
                })
        
        if transitions:
            transition_df = pd.DataFrame(transitions)
            
            return {
                'average_transition_time': transition_df['transition_time'].mean(),
                'transition_time_distribution': transition_df['transition_time'].describe().to_dict(),
                'quality_impact': transition_df.groupby('dig_quality')['transition_time'].mean().to_dict() if 'dig_quality' in transition_df.columns else {},
                'tempo_preferences': transition_df.groupby('set_tempo')['transition_time'].mean().to_dict()
            }
        
        return {}
    
    def extract_serve_sequences(self, tactical_data: pd.DataFrame) -> List[List[str]]:
        """Extract serve-to-rally sequences"""
        
        sequences = []
        current_sequence = []
        
        for _, action in tactical_data.iterrows():
            if action['action_type'] == 'serve':
                if current_sequence:
                    sequences.append(current_sequence)
                current_sequence = ['serve']
            else:
                if current_sequence:
                    current_sequence.append(action['action_type'])
        
        if current_sequence:
            sequences.append(current_sequence)
        
        return sequences
    
    def extract_attack_transitions(self, tactical_data: pd.DataFrame) -> List[Dict]:
        """Extract attack transition patterns"""
        
        transitions = []
        
        for i in range(len(tactical_data) - 2):
            reception = tactical_data.iloc[i]
            setting = tactical_data.iloc[i + 1]
            attack = tactical_data.iloc[i + 2]
            
            if (reception['action_type'] == 'reception' and 
                setting['action_type'] == 'set' and 
                attack['action_type'] == 'attack'):
                
                transitions.append({
                    'reception_quality': reception['quality'],
                    'set_tempo': setting['tempo'],
                    'attack_zone': attack['zone'],
                    'attack_quality': attack['quality'],
                    'transition_time': attack['timestamp'] - reception['timestamp']
                })
        
        return transitions
    
    def analyze_reception_vs_serve(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze reception effectiveness vs serve type"""
        
        results = {}
        
        # Find serve-reception pairs
        for i in range(len(tactical_data) - 1):
            serve = tactical_data.iloc[i]
            reception = tactical_data.iloc[i + 1]
            
            if serve['action_type'] == 'serve' and reception['action_type'] == 'reception':
                serve_type = serve['tempo']
                reception_quality = reception['quality']
                
                if serve_type not in results:
                    results[serve_type] = []
                results[serve_type].append(reception_quality)
        
        # Calculate effectiveness
        effectiveness = {}
        for serve_type, qualities in results.items():
            effectiveness[serve_type] = np.mean(qualities) if qualities else 2.0
        
        return effectiveness
    
    def analyze_reception_formation(self, tactical_data: pd.DataFrame) -> Dict:
        """Analyze reception formation patterns"""
        
        reception_data = tactical_data[tactical_data['action_type'] == 'reception']
        
        if reception_data.empty:
            return {}
        
        return {
            'zone_coverage': reception_data['zone'].value_counts().to_dict(),
            'player_zone_assignments': reception_data.groupby('player_id')['zone'].apply(list).to_dict(),
            'formation_effectiveness': reception_data.groupby('zone')['quality'].mean().to_dict()
        }
    
    def compare_to_benchmarks(self, tactical_data: pd.DataFrame) -> Dict:
        """Compare tactical performance to FIVB benchmarks"""
        
        comparisons = {}
        
        for action_type in ['serve', 'attack', 'reception', 'set']:
            action_data = tactical_data[tactical_data['action_type'] == action_type]
            
            if action_data.empty:
                continue
            
            benchmark = self.tactical_benchmarks.get(action_type, {})
            
            if action_type == 'serve':
                comparisons['serve'] = self.compare_serve_to_benchmark(action_data, benchmark)
            elif action_type == 'attack':
                comparisons['attack'] = self.compare_attack_to_benchmark(action_data, benchmark)
            elif action_type == 'reception':
                comparisons['reception'] = self.compare_reception_to_benchmark(action_data, benchmark)
            elif action_type == 'set':
                comparisons['set'] = self.compare_set_to_benchmark(action_data, benchmark)
        
        return comparisons
    
    def compare_serve_to_benchmark(self, serve_data: pd.DataFrame, benchmark: Dict) -> Dict:
        """Compare serve performance to benchmarks"""
        
        return {
            'zone_distribution_comparison': self.compare_distributions(
                serve_data['zone'].value_counts(normalize=True).to_dict(),
                benchmark.get('zones', {})
            ),
            'quality_vs_benchmark': {
                'actual': serve_data['quality'].mean(),
                'benchmark': 2.5,  # Expected average quality
                'difference': serve_data['quality'].mean() - 2.5
            },
            'effectiveness_score': self.calculate_effectiveness_score(serve_data, benchmark)
        }
    
    def compare_attack_to_benchmark(self, attack_data: pd.DataFrame, benchmark: Dict) -> Dict:
        """Compare attack performance to benchmarks"""
        
        return {
            'tempo_distribution_comparison': self.compare_distributions(
                attack_data['tempo'].value_counts(normalize=True).to_dict(),
                benchmark.get('tempo_distribution', {})
            ),
            'zone_effectiveness': attack_data.groupby('zone')['quality'].mean().to_dict(),
            'kill_rate_estimate': (attack_data['quality'] == 3).sum() / len(attack_data),
            'benchmark_kill_rate': benchmark.get('kill_rate', 0.45)
        }
    
    def compare_reception_to_benchmark(self, reception_data: pd.DataFrame, benchmark: Dict) -> Dict:
        """Compare reception performance to benchmarks"""
        
        return {
            'quality_distribution_comparison': self.compare_distributions(
                reception_data['quality'].value_counts(normalize=True).to_dict(),
                benchmark.get('quality_distribution', {1: 0.3, 2: 0.45, 3: 0.25})
            ),
            'perfect_pass_rate': (reception_data['quality'] == 3).sum() / len(reception_data),
            'benchmark_perfect_rate': benchmark.get('perfect_pass_rate', 0.25),
            'error_rate': (reception_data['quality'] == 1).sum() / len(reception_data),
            'benchmark_error_rate': benchmark.get('error_rate', 0.08)
        }
    
    def compare_set_to_benchmark(self, set_data: pd.DataFrame, benchmark: Dict) -> Dict:
        """Compare setting performance to benchmarks"""
        
        return {
            'tempo_accuracy': set_data.groupby('tempo')['quality'].mean().to_dict(),
            'benchmark_tempo_accuracy': benchmark.get('tempo_accuracy', {}),
            'overall_quality': set_data['quality'].mean(),
            'benchmark_quality': 2.7
        }
    
    def compare_distributions(self, actual: Dict, benchmark: Dict) -> Dict:
        """Compare two probability distributions"""
        
        # Normalize both to sum to 1
        actual_total = sum(actual.values())
        if actual_total > 0:
            actual_norm = {k: v/actual_total for k, v in actual.items()}
        else:
            actual_norm = actual
        
        benchmark_total = sum(benchmark.values())
        if benchmark_total > 0:
            benchmark_norm = {k: v/benchmark_total for k, v in benchmark.items()}
        else:
            benchmark_norm = benchmark
        
        # Calculate differences
        all_keys = set(actual_norm.keys()) | set(benchmark_norm.keys())
        differences = {}
        
        for key in all_keys:
            actual_val = actual_norm.get(key, 0.0)
            benchmark_val = benchmark_norm.get(key, 0.0)
            differences[key] = {
                'actual': actual_val,
                'benchmark': benchmark_val,
                'difference': actual_val - benchmark_val
            }
        
        return differences
    
    def calculate_effectiveness_score(self, action_data: pd.DataFrame, benchmark: Dict) -> float:
        """Calculate overall effectiveness score"""
        
        # Weight different factors
        quality_weight = 0.4
        consistency_weight = 0.3
        tactical_adherence_weight = 0.3
        
        # Quality score
        quality_score = action_data['quality'].mean() / 3.0  # Normalize to 0-1
        
        # Consistency score (inverse of variance)
        quality_variance = action_data['quality'].var()
        consistency_score = max(0, 1.0 - quality_variance / 2.0)  # Lower variance = higher consistency
        
        # Tactical adherence score (how well actions follow expected patterns)
        # This would be more sophisticated in production
        tactical_adherence = 0.7  # Placeholder
        
        effectiveness = (
            quality_weight * quality_score +
            consistency_weight * consistency_score +
            tactical_adherence_weight * tactical_adherence
        )
        
        return effectiveness
    
    def generate_tactical_insights(self, tactical_data: pd.DataFrame, patterns: Dict) -> List[str]:
        """Generate tactical insights for coaching"""
        
        insights = []
        
        # Serve insights
        if 'serve' in patterns:
            serve_patterns = patterns['serve']
            
            if serve_patterns.get('zone_distribution'):
                most_common_zone = max(serve_patterns['zone_distribution'], key=serve_patterns['zone_distribution'].get)
                insights.append(f"Most serves directed to zone {most_common_zone} - consider varying serve placement")
            
            avg_serve_quality = tactical_data[tactical_data['action_type'] == 'serve']['quality'].mean()
            if avg_serve_quality < 2.0:
                insights.append(f"Serve quality below average ({avg_serve_quality:.1f}/3) - focus on serve consistency training")
        
        # Attack insights
        if 'attack' in patterns:
            attack_patterns = patterns['attack']
            
            if attack_patterns.get('tempo_distribution'):
                tempo_dist = attack_patterns['tempo_distribution']
                if tempo_dist.get('high_ball', 0) > 0.5:
                    insights.append("High reliance on high ball attacks - consider incorporating faster tempo sets")
            
            if attack_patterns.get('zone_effectiveness'):
                zone_effectiveness = attack_patterns['zone_effectiveness']
                lowest_zone = min(zone_effectiveness, key=zone_effectiveness.get)
                insights.append(f"Lowest attack effectiveness in zone {lowest_zone} - work on approach angles for this zone")
        
        # Reception insights
        if 'reception' in patterns:
            reception_patterns = patterns['reception']
            
            perfect_pass_rate = reception_patterns.get('perfect_pass_rate', 0)
            if perfect_pass_rate < 0.2:
                insights.append(f"Perfect pass rate low ({perfect_pass_rate:.1%}) - emphasize platform technique and footwork")
            
            error_rate = reception_patterns.get('error_rate', 0)
            if error_rate > 0.1:
                insights.append(f"Reception error rate high ({error_rate:.1%}) - focus on reading server and early preparation")
        
        return insights
    
    def generate_match_summary(self, tactical_data: pd.DataFrame) -> Dict:
        """Generate high-level match summary"""
        
        total_actions = len(tactical_data)
        
        summary = {
            'total_actions': total_actions,
            'action_distribution': tactical_data['action_type'].value_counts().to_dict(),
            'average_quality': tactical_data['quality'].mean(),
            'quality_distribution': tactical_data['quality'].value_counts().to_dict(),
            'match_duration': tactical_data['timestamp'].max() - tactical_data['timestamp'].min() if total_actions > 0 else 0,
            'unique_players': len(tactical_data['player_id'].unique()),
            'rally_count': len(tactical_data.groupby(tactical_data['timestamp'].diff().gt(10).cumsum()))
        }
        
        return summary
    
    def generate_recommendations(self, tactical_data: pd.DataFrame, patterns: Dict) -> List[Dict]:
        """Generate specific training recommendations"""
        
        recommendations = []
        
        # Serve recommendations
        serve_data = tactical_data[tactical_data['action_type'] == 'serve']
        if not serve_data.empty:
            serve_quality = serve_data['quality'].mean()
            
            if serve_quality < 2.0:
                recommendations.append({
                    'category': 'serve',
                    'priority': 'high',
                    'description': 'Improve serve consistency',
                    'specific_drills': ['Target serving to zones 1, 6, 5', 'Jump serve repetition', 'Serve under pressure scenarios'],
                    'metrics_to_track': ['Serve accuracy percentage', 'Ace-to-error ratio', 'Serve velocity consistency']
                })
        
        # Attack recommendations
        attack_data = tactical_data[tactical_data['action_type'] == 'attack']
        if not attack_data.empty:
            attack_quality = attack_data['quality'].mean()
            
            if attack_quality < 2.2:
                recommendations.append({
                    'category': 'attack',
                    'priority': 'high',
                    'description': 'Enhance attack effectiveness',
                    'specific_drills': ['Approach timing drills', 'Vision training for block reading', 'Transition footwork'],
                    'metrics_to_track': ['Kill percentage', 'Attack error rate', 'Approach speed consistency']
                })
        
        # Reception recommendations
        reception_data = tactical_data[tactical_data['action_type'] == 'reception']
        if not reception_data.empty:
            reception_quality = reception_data['quality'].mean()
            
            if reception_quality < 2.0:
                recommendations.append({
                    'category': 'reception',
                    'priority': 'medium',
                    'description': 'Strengthen reception fundamentals',
                    'specific_drills': ['Platform angle drills', 'Footwork patterns', 'Reading server tendencies'],
                    'metrics_to_track': ['Perfect pass percentage', 'Reception error rate', 'Platform stability']
                })
        
        return recommendations

# Global tactical analyzer instance
tactical_analyzer = TacticalAnalyzer()

def analyze_tactical_match(dvw_file_path: str, video_path: Optional[str] = None) -> Dict:
    """Main function for tactical match analysis"""
    return tactical_analyzer.analyze_match(dvw_file_path, video_path)

def integrate_tactical_biomechanical(tactical_analysis: Dict, biomechanical_data: Dict) -> Dict:
    """Integrate tactical and biomechanical analysis"""
    
    integration = {
        'tactical_context': tactical_analysis,
        'biomechanical_data': biomechanical_data,
        'integrated_insights': [],
        'context_specific_recommendations': []
    }
    
    # Generate integrated insights
    if tactical_analysis.get('rally_analysis') and biomechanical_data.get('actions'):
        for rally in tactical_analysis['rally_analysis']:
            # Find corresponding biomechanical actions
            rally_actions = [
                action for action in biomechanical_data['actions']
                if rally.start_time <= action.get('timestamp', 0) <= rally.end_time
            ]
            
            for action in rally_actions:
                # Combine tactical context with biomechanical analysis
                integrated_insight = {
                    'timestamp': action.get('timestamp'),
                    'tactical_context': {
                        'set_tempo': rally.set_tempo,
                        'attack_zone': rally.attack_zone,
                        'reception_quality': rally.reception_quality
                    },
                    'biomechanical_analysis': action.get('analysis', {}),
                    'integrated_assessment': generate_integrated_assessment(rally, action)
                }
                
                integration['integrated_insights'].append(integrated_insight)
    
    return integration

def generate_integrated_assessment(rally_context: RallyContext, biomechanical_action: Dict) -> str:
    """Generate integrated tactical-biomechanical assessment"""
    
    # This would use LLM in production to generate contextual feedback
    # For now, return structured assessment
    
    assessment = {
        'tempo_impact': f"Set tempo: {rally_context.set_tempo}",
        'zone_specific': f"Attack zone: {rally_context.attack_zone}",
        'quality_context': f"Reception quality: {rally_context.reception_quality}/3",
        'biomechanical_deviations': biomechanical_action.get('deviations', {}),
        'tactical_recommendation': generate_tactical_recommendation(rally_context, biomechanical_action)
    }
    
    return str(assessment)

def generate_tactical_recommendation(rally_context: RallyContext, biomechanical_action: Dict) -> str:
    """Generate tactical recommendation based on context"""
    
    # Fast tempo with poor reception
    if rally_context.set_tempo == 'first_tempo' and rally_context.reception_quality < 2:
        return "Consider slower tempo when reception quality is poor to allow better approach timing"
    
    # High ball with zone 2 attack
    if rally_context.set_tempo == 'high_ball' and rally_context.attack_zone == 2:
        return "High ball to zone 2 allows maximum approach time - focus on full approach mechanics"
    
    # Poor reception quality
    if rally_context.reception_quality == 1:
        return "Poor reception limits setter options - work on reception platform and footwork"
    
    return "Maintain current tactical approach while addressing biomechanical deviations"
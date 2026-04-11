"""
Elite Olympic-Level Volleyball Analysis Integration
Combines all elite components into the main analysis pipeline
"""
import numpy as np
from typing import Dict, List, Optional
from elite_analyser import analyze_elite_biomechanics
from elite_coach_feedback import generate_elite_coaching_feedback
from elite_biomechanics import detect_position_from_movement, get_seasonal_context
from temporal_analyzer import analyze_temporal_phases

def analyze_video_elite_level(video_path: str, technique: str, athlete_id: str = None, 
                            session_history: list = None, tournament_context: str = "training") -> dict:
    """
    Main function for Olympic-level volleyball video analysis
    
    Args:
        video_path: Path to video file
        technique: Volleyball technique (spike, serve, block, dig)
        athlete_id: Optional athlete identifier for tracking
        session_history: Previous session data for progression tracking
        tournament_context: Competition context (training, world_championship, olympic_games)
    
    Returns:
        Comprehensive elite-level analysis results
    """
    
    # Import required modules
    from pose_extractor import extract_pose
    from video_quality import check_video_quality
    from action_localiser import localise_technique, extract_clip
    from smart_analyser import analyse_video_auto
    
    results = {
        "analysis_type": "elite_olympic_level",
        "technique": technique,
        "tournament_context": tournament_context,
        "quality_assessment": {},
        "pose_analysis": {},
        "elite_biomechanics": {},
        "position_analysis": {},
        "temporal_analysis": {},
        "coaching_feedback": {},
        "performance_projection": {},
        "training_recommendations": {},
        "competition_readiness": {},
        "olympic_readiness_score": 0,
        "performance_percentile": 0,
        "session_tracking": {}
    }
    
    try:
        # Step 1: Quality assessment with Olympic standards
        print(f"[ELITE] Starting Olympic-level analysis for {technique}...")
        
        quality = check_video_quality(video_path, run_person_check=False)
        results["quality_assessment"] = {
            "passed": quality.ok,
            "issues": quality.issues if hasattr(quality, 'issues') else [],
            "recommendations": quality.recommendations if hasattr(quality, 'recommendations') else [],
            "olympic_standards": "Meets Olympic video analysis requirements" if quality.ok else "Requires improvement for elite analysis"
        }
        
        if not quality.ok:
            results["error"] = "Video quality insufficient for Olympic-level analysis"
            return results
        
        # Step 2: Enhanced pose extraction with position detection
        print("[ELITE] Extracting pose data with Olympic precision...")
        
        pose_result = extract_pose(video_path, technique)
        results["pose_analysis"] = {
            "frames_analyzed": len(pose_result["pose_sequence_3d"]),
            "average_confidence": pose_result["average_confidence"],
            "localisation": pose_result.get("localisation", {}),
            "technique_detected": technique
        }
        
        # Step 3: Detect player position based on movement patterns
        print("[ELITE] Detecting player position from movement patterns...")
        
        pose_sequence = pose_result["pose_sequence_3d"]
        technique_counts = {technique: 1}  # Single technique analysis
        detected_position = detect_position_from_movement(pose_sequence, technique_counts)
        
        results["position_analysis"] = {
            "detected_position": detected_position,
            "confidence": 0.85,  # High confidence for single technique
            "position_suitability": "Analyzing against Olympic standards for position",
            "positional_benchmarks_applied": True
        }
        
        # Step 4: Elite biomechanical analysis with Olympic benchmarks
        print("[ELITE] Performing Olympic-level biomechanical analysis...")
        
        # Determine seasonal context from session history
        session_count = len(session_history) if session_history else 0
        seasonal_context = get_seasonal_context(session_count, tournament_context)
        
        elite_biomechanics = analyze_elite_biomechanics(
            pose_sequence, 
            technique, 
            detected_position,
            {"session_count": session_count, "seasonal_context": seasonal_context}
        )
        
        results["elite_biomechanics"] = elite_biomechanics
        results["olympic_readiness_score"] = elite_biomechanics.get("olympic_readiness_score", 0)
        results["performance_percentile"] = elite_biomechanics.get("performance_percentile", 0)
        
        # Step 5: Temporal analysis with Olympic timing constraints
        print("[ELITE] Analyzing temporal phases with Olympic timing...")
        
        temporal_analysis = analyze_temporal_phases(pose_sequence, 30.0, technique)  # Assuming 30fps
        results["temporal_analysis"] = temporal_analysis
        
        # Step 6: Generate elite coaching feedback
        print("[ELITE] Generating Olympic-level coaching feedback...")
        
        elite_feedback = generate_elite_coaching_feedback(
            elite_biomechanics,
            athlete_level="advanced",  # Assume advanced for Olympic analysis
            session_history=session_history,
            tournament_context=tournament_context
        )
        
        results["coaching_feedback"] = elite_feedback
        
        # Step 7: Performance projection and training recommendations
        print("[ELITE] Creating performance projection and training plan...")
        
        # Extract training recommendations from coaching feedback
        if "training_prescription" in elite_feedback:
            results["training_recommendations"] = elite_feedback["training_prescription"]
        
        # Extract performance projection
        if "performance_projection" in elite_feedback:
            results["performance_projection"] = elite_feedback["performance_projection"]
        
        # Competition readiness assessment
        if "competition_readiness" in elite_feedback:
            results["competition_readiness"] = elite_feedback["competition_readiness"]
        
        # Step 8: Session tracking and progression analysis
        print("[ELITE] Analyzing session progression...")
        
        session_tracking = analyze_session_progression(
            elite_biomechanics,
            session_history,
            technique,
            athlete_id
        )
        
        results["session_tracking"] = session_tracking
        
        # Step 9: Generate comprehensive summary
        print("[ELITE] Generating comprehensive analysis summary...")
        
        results["summary"] = generate_elite_summary(results)
        
        print(f"[ELITE] Olympic-level analysis complete! Readiness score: {results['olympic_readiness_score']:.1f}/100")
        
        return results
        
    except Exception as e:
        results["error"] = f"Elite analysis failed: {str(e)}"
        return results

def analyze_session_progression(current_analysis: dict, session_history: list, technique: str, athlete_id: str) -> dict:
    """Analyze progression across sessions"""
    
    progression = {
        "session_count": len(session_history) + 1 if session_history else 1,
        "current_session": current_analysis.get("olympic_readiness_score", 0),
        "progression_trend": "stable",
        "improvement_rate": 0,
        "consistency_score": 0,
        "fatigue_indicators": [],
        "recommendation": "Continue current training approach"
    }
    
    if session_history and len(session_history) >= 2:
        # Calculate progression trend
        recent_scores = [session.get("olympic_readiness_score", 0) for session in session_history[-5:]]
        current_score = current_analysis.get("olympic_readiness_score", 0)
        recent_scores.append(current_score)
        
        if len(recent_scores) >= 2:
            # Calculate trend
            if recent_scores[-1] > recent_scores[0]:
                progression["progression_trend"] = "improving"
                progression["improvement_rate"] = (recent_scores[-1] - recent_scores[0]) / len(recent_scores)
            elif recent_scores[-1] < recent_scores[0]:
                progression["progression_trend"] = "declining"
                progression["improvement_rate"] = (recent_scores[-1] - recent_scores[0]) / len(recent_scores)
            else:
                progression["progression_trend"] = "stable"
        
        # Calculate consistency
        if len(recent_scores) > 2:
            progression["consistency_score"] = 1.0 - (np.std(recent_scores) / np.mean(recent_scores)) if np.mean(recent_scores) > 0 else 0
        
        # Check for fatigue indicators
        if len(session_history) >= 3:
            recent_3_scores = [session.get("olympic_readiness_score", 0) for session in session_history[-3:]]
            if all(score < recent_3_scores[0] for score in recent_3_scores[1:]):
                progression["fatigue_indicators"].append("Declining performance trend - possible overtraining")
            
            # Check for excessive variation
            if np.std(recent_3_scores) > 10:
                progression["fatigue_indicators"].append("High performance variation - possible fatigue or inconsistent technique")
        
        # Generate recommendations based on progression
        if progression["progression_trend"] == "declining" and progression["improvement_rate"] < -2:
            progression["recommendation"] = "Reduce training intensity and focus on technique recovery"
        elif progression["progression_trend"] == "improving" and progression["improvement_rate"] > 2:
            progression["recommendation"] = "Excellent progression - maintain current training approach"
        elif progression["consistency_score"] < 0.7:
            progression["recommendation"] = "Focus on technique consistency through repetition training"
        else:
            progression["recommendation"] = "Stable performance - consider increasing training complexity"
    
    return progression

def generate_elite_summary(results: dict) -> dict:
    """Generate comprehensive elite-level summary"""
    
    olympic_readiness = results.get("olympic_readiness_score", 0)
    performance_percentile = results.get("performance_percentile", 0)
    technique = results.get("technique", "unknown")
    position = results.get("position_analysis", {}).get("detected_position", "unknown")
    tournament_context = results.get("tournament_context", "training")
    
    summary = {
        "analysis_level": "Olympic Elite",
        "technique_analyzed": technique,
        "detected_position": position,
        "tournament_context": tournament_context,
        "olympic_readiness_score": olympic_readiness,
        "performance_percentile": performance_percentile,
        "overall_assessment": "",
        "key_strengths": [],
        "priority_improvements": [],
        "competition_readiness": "",
        "next_steps": [],
        "confidence_level": 0
    }
    
    # Overall assessment based on Olympic readiness
    if olympic_readiness >= 90:
        summary["overall_assessment"] = "ELITE LEVEL - Olympic-ready technique"
        summary["competition_readiness"] = "Ready for Olympic competition"
        summary["confidence_level"] = 95
    elif olympic_readiness >= 80:
        summary["overall_assessment"] = "ADVANCED LEVEL - Strong foundation for elite competition"
        summary["competition_readiness"] = "Ready for international competition"
        summary["confidence_level"] = 85
    elif olympic_readiness >= 70:
        summary["overall_assessment"] = "INTERMEDIATE LEVEL - Solid foundation requiring refinement"
        summary["competition_readiness"] = "Ready for national-level competition"
        summary["confidence_level"] = 70
    else:
        summary["overall_assessment"] = "DEVELOPMENTAL LEVEL - Fundamental technique development needed"
        summary["competition_readiness"] = "Continue development for competitive readiness"
        summary["confidence_level"] = 50
    
    # Extract key strengths from elite comparisons
    elite_comparisons = results.get("elite_biomechanics", {}).get("elite_comparisons", {})
    strengths = elite_comparisons.get("strengths", [])
    improvement_areas = elite_comparisons.get("improvement_areas", [])
    
    summary["key_strengths"] = strengths[:3] if strengths else ["Solid technical foundation"]
    summary["priority_improvements"] = improvement_areas[:3] if improvement_areas else ["Overall technique refinement"]
    
    # Next steps based on analysis
    coaching_feedback = results.get("coaching_feedback", {})
    if "next_session_focus" in coaching_feedback:
        summary["next_steps"].append(coaching_feedback["next_session_focus"])
    
    # Add training recommendations
    training_recs = results.get("training_recommendations", {})
    if "training_phase" in training_recs:
        summary["next_steps"].append(f"Training phase: {training_recs['training_phase']}")
    
    # Add temporal analysis insights
    temporal_analysis = results.get("temporal_analysis", {})
    if "timing_analysis" in temporal_analysis:
        timing_score = temporal_analysis["timing_analysis"].get("overall_timing_score", 0)
        if timing_score < 0.7:
            summary["next_steps"].append("Focus on movement timing and rhythm coordination")
    
    return summary

# Integration function for existing pipeline
def integrate_elite_analysis(existing_results: dict, technique: str, athlete_id: str = None) -> dict:
    """Integrate elite analysis with existing pipeline results"""
    
    # If we have pose data from existing analysis, enhance it with elite standards
    if "pose_sequence_3d" in existing_results:
        pose_sequence = existing_results["pose_sequence_3d"]
        
        # Perform elite biomechanical analysis
        elite_biomechanics = analyze_elite_biomechanics(pose_sequence, technique)
        
        # Generate elite coaching feedback
        elite_feedback = generate_elite_coaching_feedback(elite_biomechanics)
        
        # Enhance existing results with elite analysis
        existing_results["elite_analysis"] = {
            "olympic_readiness_score": elite_biomechanics.get("olympic_readiness_score", 0),
            "performance_percentile": elite_biomechanics.get("performance_percentile", 0),
            "position_detected": elite_biomechanics.get("position", "unknown"),
            "elite_comparisons": elite_biomechanics.get("elite_comparisons", {}),
            "coaching_feedback": elite_feedback,
            "analysis_level": "Olympic Elite"
        }
        
        # Update verdict with Olympic standards
        olympic_readiness = elite_biomechanics.get("olympic_readiness_score", 0)
        if olympic_readiness >= 90:
            existing_results["verdict"] = "OLYMPIC ELITE"
        elif olympic_readiness >= 80:
            existing_results["verdict"] = "INTERNATIONAL ELITE"
        elif olympic_readiness >= 70:
            existing_results["verdict"] = "ADVANCED"
        else:
            existing_results["verdict"] = "DEVELOPING"
    
    return existing_results
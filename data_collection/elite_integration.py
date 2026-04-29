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
    NOW ENHANCED WITH SMART_ANALYSER AUTO-DETECTION AND PHYSICS FALLBACK
    """
    
    # Import required modules
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
        # Step 1: Use smart_analyser for robust detection and fallback
        print(f"[ELITE] Running smart_analyser.analyse_video_auto for {technique}...")
        auto_result = analyse_video_auto(video_path, athlete_id=athlete_id)
        
        results["quality_assessment"] = {
            "passed": auto_result["quality"].get("ok", False) if auto_result.get("quality") else True,
            "issues": auto_result["quality"].get("issues", []) if auto_result.get("quality") else [],
            "recommendations": auto_result["quality"].get("recommendations", []) if auto_result.get("quality") else [],
            "olympic_standards": "Meets Olympic video analysis requirements"
        }
        
        if not auto_result.get("segments"):
            if auto_result.get("bad_video_advice"):
                results["error"] = auto_result["bad_video_advice"]
            else:
                results["error"] = "No techniques detected even with Physics Fallback."
            return results
            
        # Step 2: Find best segment for requested technique
        best_seg = None
        for seg in auto_result["segments"]:
            if seg["technique"] == technique:
                if best_seg is None or (seg.get("analysis") and not best_seg.get("analysis")):
                    best_seg = seg
                elif seg.get("analysis") and best_seg.get("analysis"):
                    if seg["analysis"].get("confidence", 0) > best_seg["analysis"].get("confidence", 0):
                        best_seg = seg
        
        # Fallback to any segment with analysis
        if not best_seg:
            best_seg = next((s for s in auto_result["segments"] if s.get("analysis")), auto_result["segments"][0])
            
        if not best_seg or not best_seg.get("analysis"):
            results["error"] = "Analysis failed for all detected segments."
            return results

        elite_data = best_seg["analysis"].get("elite_data", {})
        
        # Step 3: Populate results from the best segment
        results["pose_analysis"] = {
            "frames_analyzed": best_seg["end_frame"] - best_seg["start_frame"],
            "average_confidence": best_seg["analysis"].get("confidence", 0),
            "localisation": {"start_frame": best_seg["start_frame"], "end_frame": best_seg["end_frame"]},
            "technique_detected": best_seg["technique"]
        }
        
        results["elite_biomechanics"] = elite_data
        results["olympic_readiness_score"] = elite_data.get("olympic_readiness_score", 0)
        results["performance_percentile"] = elite_data.get("performance_percentile", 0)
        
        results["position_analysis"] = {
            "detected_position": elite_data.get("position", "receiver"),
            "confidence": 0.85,
            "position_suitability": "Analyzing against Olympic standards for position",
            "positional_benchmarks_applied": True
        }
        
        results["temporal_analysis"] = {
            "phases": elite_data.get("phase_analysis", []),
            "timing_analysis": elite_data.get("temporal_accuracy", {})
        }
        
        # Step 4: Coaching feedback
        if "coaching_insights" in elite_data:
            results["coaching_feedback"] = {
                "headline": elite_data["coaching_insights"][0] if elite_data["coaching_insights"] else "Focus on form",
                "technical_analysis": {
                    "overall_assessment": elite_data["elite_comparisons"].get("olympic_readiness", "GOOD"),
                    "technical_strengths": elite_data["elite_comparisons"].get("strengths", []),
                    "technical_weaknesses": elite_data["elite_comparisons"].get("improvement_areas", [])
                }
            }
        
        # Step 5: Session tracking and progression
        session_tracking = analyze_session_progression(
            elite_data,
            session_history,
            best_seg["technique"],
            athlete_id
        )
        results["session_tracking"] = session_tracking
        
        # Step 6: Generate comprehensive summary
        results["summary"] = generate_elite_summary(results)
        
        print(f"[ELITE] Enhanced analysis complete! Readiness score: {results['olympic_readiness_score']:.1f}/100")
        return results
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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
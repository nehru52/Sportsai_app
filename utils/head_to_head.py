class HeadToHeadComparator:
    """
    Compares two athlete profiles side-by-side across key biomechanical metrics.
    """
    def __init__(self, aggregator):
        self.aggregator = aggregator

    def compare(self, track_id_a: str, track_id_b: str) -> dict:
        pa = self.aggregator.get_player_profile(track_id_a)
        pb = self.aggregator.get_player_profile(track_id_b)
        
        if not pa or not pb:
            return {"error": "One or both players not found"}

        metrics_list = {
            "fivb_score": "fivb_score",
            "jump_height_normalised": "jump_height_normalised",
            "arm_cock_angle": "arm_cock_angle",
            "spike_event_count": "total_spike_events",
            "jump_event_count": "total_jump_events"
        }
        
        results = {}
        adv_a = []
        adv_b = []
        
        for label, key in metrics_list.items():
            # Get values from top level or biomechanics dict
            val_a = pa.get(key)
            if val_a is None: val_a = pa.get('biomechanics', {}).get(key, 0)
            
            val_b = pb.get(key)
            if val_b is None: val_b = pb.get('biomechanics', {}).get(key, 0)
            
            # Ensure they are numeric
            val_a = float(val_a) if val_a is not None else 0.0
            val_b = float(val_b) if val_b is not None else 0.0
            
            winner = "tied"
            if val_a > val_b: winner = track_id_a
            elif val_b > val_a: winner = track_id_b
            
            results[label] = {"a": round(val_a, 2), "b": round(val_b, 2), "winner": winner}
            
            # 10% Advantage check
            if val_a > 0 and (val_a - val_b) / max(val_a, val_b, 0.01) > 0.10:
                adv_a.append(label)
            elif val_b > 0 and (val_b - val_a) / max(val_a, val_b, 0.01) > 0.10:
                adv_b.append(label)

        # Overall Winner
        score_a = results["fivb_score"]["a"]
        score_b = results["fivb_score"]["b"]
        overall = "tied"
        if score_a > score_b: overall = track_id_a
        elif score_b > score_a: overall = track_id_b
        
        # Recommendation Heuristic
        rec = f"Player {track_id_a} and {track_id_b} are closely matched."
        if overall != "tied":
            better = track_id_a if overall == track_id_a else track_id_b
            worse = track_id_b if overall == track_id_a else track_id_a
            adv_str = ", ".join(adv_a if overall == track_id_a else adv_b)
            if adv_str:
                rec = f"Player {better} shows superior {adv_str} compared to {worse}."
            else:
                rec = f"Player {better} has a slightly higher overall efficiency score."

        return {
            "player_a": track_id_a,
            "player_b": track_id_b,
            "winner_overall": overall,
            "metrics": results,
            "advantages_a": adv_a,
            "advantages_b": adv_b,
            "recommendation": rec
        }

    def compare_many(self, track_ids: list) -> list:
        comparisons = []
        for i in range(len(track_ids)):
            for j in range(i + 1, len(track_ids)):
                comparisons.append(self.compare(track_ids[i], track_ids[j]))
        
        comparisons.sort(key=lambda x: max(x['metrics']['fivb_score']['a'], x['metrics']['fivb_score']['b']), reverse=True)
        return comparisons

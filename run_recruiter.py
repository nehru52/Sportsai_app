import argparse
import sys
from utils.player_aggregator import PlayerAggregator
from utils.head_to_head import HeadToHeadComparator
from utils.report_generator import ReportGenerator

def main():
    parser = argparse.ArgumentParser(description="Elite Volleyball Biomechanics — Recruiter CLI")
    parser.add_argument("--mode", choices=['rank', 'compare', 'report', 'squad'], required=True, 
                        help="Operation mode: rank squad, compare 2 players, generate single report, or squad HTML")
    parser.add_argument("--players", nargs='+', help="One or two track IDs for report or compare modes")
    parser.add_argument("--role", help="Filter results by player role (e.g. hitter, setter)")
    parser.add_argument("--top_n", type=int, default=10, help="Number of players to include in rankings")
    parser.add_argument("--ingest_dir", default='data/recruiter_outputs/', help="Directory containing recruiter JSON files")
    
    args = parser.parse_args()

    # 1. Initialize Core
    agg = PlayerAggregator()
    agg.ingest_all(args.ingest_dir)
    comp = HeadToHeadComparator(agg)
    rep = ReportGenerator(agg, comp)

    if not agg.players:
        print("No player data found. Ensure you have run pose_extractor.py first.")
        return

    # 2. Execute Modes
    if args.mode == 'rank':
        ranked = agg.rank_players(role=args.role, top_n=args.top_n)
        print(f"\n--- Top {args.top_n} {args.role or 'All Positions'} ---")
        print(f"{'Rank':<5} {'ID':<10} {'Role':<10} {'FIVB Score':<12} {'Frames':<10}")
        for i, p in enumerate(ranked):
            print(f"{i+1:<5} {p['track_id']:<10} {p['role']:<10} {p['fivb_score']:<12} {p['total_frames_analysed']:<10}")
        
        path = rep.generate_squad_ranking(role=args.role, top_n=args.top_n)
        print(f"\nFull squad ranking saved to: {path}")

    elif args.mode == 'compare':
        if not args.players or len(args.players) < 2:
            print("Error: --compare mode requires exactly two --players (track IDs)")
            return
        
        res = comp.compare(args.players[0], args.players[1])
        if "error" in res:
            print(f"Error: {res['error']}")
            return
            
        print(f"\n--- Comparison: {args.players[0]} vs {args.players[1]} ---")
        print(f"Winner Overall: {res['winner_overall']}")
        print(f"Recommendation: {res['recommendation']}")
        
        path = rep.generate_comparison_report(args.players[0], args.players[1])
        print(f"\nDetailed comparison report saved to: {path}")

    elif args.mode == 'report':
        if not args.players or len(args.players) < 1:
            print("Error: --report mode requires at least one --players (track ID)")
            return
        
        for tid in args.players:
            path = rep.generate_player_report(tid)
            print(f"Report for Player {tid} saved to: {path}")

    elif args.mode == 'squad':
        path = rep.generate_squad_ranking(role=args.role, top_n=args.top_n)
        print(f"Squad ranking report saved to: {path}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import os

from ds_intern.client import AzureOpenAIClient
from ds_intern.simulator import ConversationSimulator, export_logs
from ds_intern.metrics import aggregate_metrics, top_failure_modes
from ds_intern.logger import write_run_metadata


def main() -> None:
	parser = argparse.ArgumentParser(description="Run DS Intern Challenge simulations")
	parser.add_argument("--version", default="v0", choices=["v0", "v1", "v2"], help="Agent A prompt version")
	parser.add_argument("--n", type=int, default=20, help="Number of conversations")
	parser.add_argument("--max_turns", type=int, default=8, help="Max turns per conversation")
	parser.add_argument("--out", default="runs/latest", help="Output directory")
	args = parser.parse_args()

	client = AzureOpenAIClient()
	sim = ConversationSimulator(client, agent_a_version=args.version)
	logs = sim.run_many(n=args.n, max_turns=args.max_turns, version=args.version)

	out_dir = os.path.join(args.out, args.version)
	export_logs(logs, out_dir)

	agg = aggregate_metrics(logs)
	fail = top_failure_modes(logs)
	write_run_metadata(out_dir, {"aggregate": agg, "failures": fail, "version": args.version, "n": args.n})

	print("Aggregate:", agg)
	print("Top failures:", fail)
	print(f"Saved to {out_dir}")


if __name__ == "__main__":
	main()
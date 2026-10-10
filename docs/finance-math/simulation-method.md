# Simulation method

The v1 modeled-range engine supports explicit bull, base, and bear scenarios plus seeded normal Monte Carlo draws. Identical parameters and seed produce identical output in the supported runtime.

Monte Carlo output records the seed, distribution family, parameters, iteration count, input hash, and limitations. Per-period draws are bounded at a total loss. Reported outputs include terminal 5th, 50th, and 95th percentiles, mean terminal value, and modeled loss probability. These are modeled ranges, not predictions.

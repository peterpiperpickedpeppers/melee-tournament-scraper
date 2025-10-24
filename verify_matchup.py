import pandas as pd

# Read the Esper Goryo's results file
esper_df = pd.read_csv('data/RC Houston 2025/results/Esper Goryo\'s results.csv')

# Filter for matches against Azorius Blink
azorius_matches = esper_df[esper_df['OpponentDeck'] == 'Azorius Blink']

print(f"Esper Goryo's vs Azorius Blink (from Esper's perspective):")
print(f"Total matches: {len(azorius_matches)}")
print("\nWins:")
esper_wins = azorius_matches[azorius_matches['WinningDeck'] == "Esper Goryo's"]
print(f"  Count: {len(esper_wins)}")
print("\nLosses:")
esper_losses = azorius_matches[azorius_matches['WinningDeck'] == 'Azorius Blink']
print(f"  Count: {len(esper_losses)}")
print("\nDraws:")
esper_draws = azorius_matches[azorius_matches['Outcome'] == 'Draw']
print(f"  Count: {len(esper_draws)}")

print("\n" + "="*60)

# Read the Azorius Blink results file
azorius_df = pd.read_csv('data/RC Houston 2025/results/Azorius Blink results.csv')

# Filter for matches against Esper Goryo's
esper_matches = azorius_df[azorius_df['OpponentDeck'] == "Esper Goryo's"]

print(f"\nAzorius Blink vs Esper Goryo's (from Azorius's perspective):")
print(f"Total matches: {len(esper_matches)}")
print("\nWins:")
azorius_wins = esper_matches[esper_matches['WinningDeck'] == 'Azorius Blink']
print(f"  Count: {len(azorius_wins)}")
print("\nLosses:")
azorius_losses = esper_matches[esper_matches['WinningDeck'] == "Esper Goryo's"]
print(f"  Count: {len(azorius_losses)}")
print("\nDraws:")
azorius_draws = esper_matches[esper_matches['Outcome'] == 'Draw']
print(f"  Count: {len(azorius_draws)}")

print("\n" + "="*60)
print("\nVERIFICATION:")
print(f"Esper wins ({len(esper_wins)}) should equal Azorius losses ({len(azorius_losses)}): {len(esper_wins) == len(azorius_losses)}")
print(f"Azorius wins ({len(azorius_wins)}) should equal Esper losses ({len(esper_losses)}): {len(azorius_wins) == len(esper_losses)}")
print(f"Draws should be equal: {len(esper_draws) == len(azorius_draws)}")

import pandas as pd

df = pd.read_csv('data/RC Houston 2025/RC Houston 2025 pairings.csv')
print(f'Total rows: {len(df)}')

# Check for Esper Goryo's vs Azorius Blink
matches = df[
    ((df['PlayerDeck'] == "Esper Goryo's") & (df['OpponentDeck'] == 'Azorius Blink')) | 
    ((df['PlayerDeck'] == 'Azorius Blink') & (df['OpponentDeck'] == "Esper Goryo's"))
]

print(f"\nEsper Goryo's vs Azorius Blink matches: {len(matches)}")
if len(matches) > 0:
    print("\nMatches found:")
    print(matches[['Player', 'PlayerDeck', 'Opponent', 'OpponentDeck', 'Outcome', 'ResultString']].to_string())
else:
    print("\nNo direct matches found. Checking unique deck names...")
    print("\nUnique PlayerDeck values containing 'Esper':")
    esper_decks = df[df['PlayerDeck'].str.contains('Esper', na=False)]['PlayerDeck'].unique()
    for deck in sorted(esper_decks):
        print(f"  - {deck}")
    
    print("\nUnique OpponentDeck values containing 'Azorius':")
    azorius_decks = df[df['OpponentDeck'].str.contains('Azorius', na=False)]['OpponentDeck'].unique()
    for deck in sorted(azorius_decks):
        print(f"  - {deck}")

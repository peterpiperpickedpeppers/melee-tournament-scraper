import pandas as pd

# Read the pairings file
df = pd.read_csv('data/RC Houston 2025/RC Houston 2025 pairings.csv')

print(f"Before cleaning: {len(df)} rows")

# Strip whitespace from PlayerDeck and OpponentDeck columns
df['PlayerDeck'] = df['PlayerDeck'].str.strip()
df['OpponentDeck'] = df['OpponentDeck'].str.strip()

# Also strip Player and Opponent names
df['Player'] = df['Player'].str.strip()
df['Opponent'] = df['Opponent'].fillna('').str.strip()

# Strip WinningDeck
df['WinningDeck'] = df['WinningDeck'].str.strip()

# Save back to the same file
df.to_csv('data/RC Houston 2025/RC Houston 2025 pairings.csv', index=False)

print(f"After cleaning: {len(df)} rows")
print("Pairings file cleaned and saved.")

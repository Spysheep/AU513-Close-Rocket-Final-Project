import pandas as pd

def analyze_dataset():
    try:
        df = pd.read_csv('dataset_tensorflow.csv', nrows=100)
        print("--- Columns ---")
        print(df.columns.tolist())
        
        print("\n--- First 5 rows ---")
        print(df.head())
        
        # Check for time-like columns
        potential_time = [c for c in df.columns if 'time' in c.lower() or 'delay' in c.lower()]
        print(f"\nPotential Time Columns: {potential_time}")
        
        if potential_time:
            t = df[potential_time[0]]
            dt_series = t.diff().dropna()
            print(f"DT Stats:\n{dt_series.value_counts()}")
            print(f"Mean DT: {dt_series.mean()}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_dataset()

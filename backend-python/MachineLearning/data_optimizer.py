import pandas as pd

# 1. Configuration des fichiers
input_file_name = 'dataset_tensorflow.csv'
output_file_name = 'dataset_tensorflow_optimized.csv'

# 2. Chargement du dataset
try:
    df = pd.read_csv(input_file_name)

    print(f"Taille de la mémoire avant optimisation: {df.memory_usage(deep=True).sum() / 1024 ** 2:.2f} MB")

    # --- A. Réduction de la Mémoire (Downcasting) ---
    # Convertir les types de données pour économiser de la mémoire (float64 -> float32, int64 -> int32)
    for col in df.columns:
        col_type = df[col].dtype

        if col_type == 'float64':
            df[col] = df[col].astype('float32')
        elif col_type == 'int64':
            # Conversion à int32 si la plage de valeurs est suffisante
            if df[col].max() < 2147483647 and df[col].min() > -2147483648:
                df[col] = df[col].astype('int32')

    # --- B. Sélection et Suppression de Features ---
    # Supprimer les identifiants qui ne contribuent pas à la prédiction
    columns_to_drop = ['rocket_id', 'simulation_id']
    df = df.drop(columns=columns_to_drop, errors='ignore')

    # --- C. Encodage des Variables Catégorielles (One-Hot Encoding) ---
    categorical_cols = ['motor_name', 'fin_cat', 'trigger']

    # One-Hot Encoding crée de nouvelles colonnes binaires pour chaque catégorie.
    df_optimized = pd.get_dummies(df, columns=categorical_cols, drop_first=False)

    # --- D. Sauvegarde du fichier optimisé ---
    print(
        f"\nTaille de la mémoire après optimisation (estimée): {df_optimized.memory_usage(deep=True).sum() / 1024 ** 2:.2f} MB")

    df_optimized.to_csv(output_file_name, index=False)

    print(f"\n✅ Optimisation terminée. Le dataset transformé a été sauvegardé sous : {output_file_name}")

except FileNotFoundError:
    print(
        f"Erreur : Le fichier '{input_file_name}' n'a pas été trouvé. Assurez-vous qu'il est dans le même répertoire que ce script.")
except Exception as e:
    print(f"Une erreur est survenue lors de l'exécution : {e}")
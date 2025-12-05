import pandas as pd

# Assurez-vous que le nom du fichier ci-dessous est correct
file_name = 'dataset_tensorflow.csv'

try:
    df = pd.read_csv(file_name)

    print("--- Aperçu des 5 premières lignes du dataset ---")
    # Afficher les premières lignes
    print(df.head().to_markdown(index=False, numalign="left", stralign="left"))

    print("\n--- Informations sur les colonnes et les types de données ---")
    # Afficher les types de données et les valeurs non nulles
    df.info()

except FileNotFoundError:
    print(f"Erreur : Le fichier '{file_name}' n'a pas été trouvé. Veuillez vérifier le nom du fichier.")
except Exception as e:
    print(f"Une erreur est survenue lors du chargement : {e}")
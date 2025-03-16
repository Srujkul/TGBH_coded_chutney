import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def generate_heatmap(csv_file):
    # Load the CSV file into a DataFrame
    df = pd.read_csv(csv_file)
    
    # Compute the correlation matrix
    correlation_matrix = df.corr()
    
    # Plot the heatmap
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
    plt.title('Heatmap of Feature Correlations')
    plt.show()

# Example usage
csv_file = "D:/PES Academy/TGBH/Project/archive/All-time Table-Bangalore-Wards.csv"  # Replace with your actual file path
generate_heatmap(csv_file)

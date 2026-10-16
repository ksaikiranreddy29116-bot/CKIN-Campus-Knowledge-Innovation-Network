from src.train_model import train_and_save_model

if __name__ == '__main__':
    print("Training ML Recommendation Models for CKIN...")
    artifact = train_and_save_model()
    print(f"Model Training Complete! Selected Model: {artifact['model_name']}")
    print(f"Metrics: {artifact['metrics']}")

from energyAgent import EnergyAgent
import config

def main():
    """
    Initializes and runs the EnergyAgent pipeline.
    """
    print("============================================================")
    print("      🚀 INITIATING ENERGY DATA TRANSFORMATION AGENT 🚀     ")
    print("============================================================")
    
    agent = EnergyAgent(config)
    success = agent.run_complete_pipeline()

    if success:
        summary = agent.get_data_summary()
        print("\n📊 FINAL SUMMARY:")
        for key, value in summary.items():
            # Format the key for better readability
            formatted_key = key.replace('_', ' ').title()
            print(f"  - {formatted_key}: {value}")
        print("\n============================================================")
    else:
        print("\n❌ Pipeline execution failed.")

if __name__ == "__main__":
    main()
from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import litellm
try:
    from .tools import RagSearchTool
except Exception:  
    from tools import RagSearchTool
from dotenv import load_dotenv
load_dotenv()

# Configure LiteLLM for LM Studio
# LM Studio runs an OpenAI-compatible API server
model_name = os.getenv('MODEL', 'lm-studio/llama-3.2-1b-instruct')
api_base = os.getenv('LMSTUDIO_API_BASE', os.getenv('LITELLM_BASE_URL', 'http://127.0.0.1:1234/v1'))
api_key = os.getenv('LMSTUDIO_API_KEY', os.getenv('LM_STUDIO_API_KEY', 'lm-studio'))

# Set environment variables for LiteLLM to recognize lm-studio provider
os.environ['LM_STUDIO_API_BASE'] = api_base
os.environ['LM_STUDIO_API_KEY'] = api_key

# Configure LiteLLM custom providers properly
litellm.custom_llm_provider = "lm-studio"
litellm.api_base = api_base
litellm.api_key = api_key

# Map lm-studio provider to openai for LiteLLM compatibility
if model_name.startswith('lm-studio/'):
    # Extract the actual model name and use openai provider
    actual_model = model_name.replace('lm-studio/', '')
    final_model = f"openai/{actual_model}"
else:
    final_model = model_name
    
print(f"Using model: {final_model} with API base: {api_base}")

#call to the local LM Studio model using env vars from your .env
# Using corrected model format for LiteLLM compatibility
try:
    ollama_llm = LLM(
        model=final_model,
        base_url=api_base,
        api_key=api_key,
    )
    print(f"Successfully initialized LLM with model: {final_model}")
except Exception as e:
    print(f"Warning: Failed to initialize LLM with {final_model}: {e}")
    # Fallback: Try with basic openai prefix
    try:
        basic_model = model_name.split('/')[-1]  # Get just the model name
        fallback_model = f"openai/{basic_model}"
        ollama_llm = LLM(
            model=fallback_model,
            base_url=api_base,
            api_key=api_key,
        )
        print(f"Successfully initialized LLM with fallback model: {fallback_model}")
    except Exception as e2:
        print(f"Error: All LLM initialization attempts failed: {e2}")
        raise Exception(f"Could not initialize LLM model. Please check your LM Studio configuration and ensure it's running on the specified port. Errors: {e}, {e2}")


@CrewBase
class AiLatestDevelopment():
    """AiLatestDevelopment crew"""

    agents: List[BaseAgent]
    tasks: List[Task]
    
    def __init__(self):
        super().__init__()
        # Debug: Check if configs are loaded properly
        try:
            print(f"agents_config type: {type(self.agents_config)}")
            print(f"tasks_config type: {type(self.tasks_config)}")
            if hasattr(self, 'agents_config') and isinstance(self.agents_config, dict):
                print(f"Available agents: {list(self.agents_config.keys())}")
            if hasattr(self, 'tasks_config') and isinstance(self.tasks_config, dict):
                print(f"Available tasks: {list(self.tasks_config.keys())}")
        except Exception as e:
            print(f"Error checking configs: {e}")

    #Agent 1
    @agent
    def ai_risk_assessment_analyst(self) -> Agent:
        try:
            print(f"Creating ai_risk_assessment_analyst agent...")
            print(f"Config type: {type(self.agents_config)}")
            if isinstance(self.agents_config, dict):
                config_data = self.agents_config['ai_risk_assessment_analyst']
                print(f"Agent config: {config_data}")
            else:
                print(f"agents_config is not a dict: {self.agents_config}")
                
            return Agent(
                config=self.agents_config['ai_risk_assessment_analyst'],
                llm=ollama_llm,
                verbose=True,
            )
        except Exception as e:
            print(f"Error creating ai_risk_assessment_analyst: {e}")
            print(f"agents_config: {self.agents_config}")
            raise

    #Agent 2
    @agent
    def ai_compliance_researcher(self) -> Agent:
        try:
            print(f"Creating ai_compliance_researcher agent...")
            return Agent(
                config=self.agents_config['ai_compliance_researcher'],
                llm=ollama_llm,
                # tools=[RagSearchTool()],  # Temporarily disabled due to ChromaDB issues
                verbose=True,
            )
        except Exception as e:
            print(f"Error creating ai_compliance_researcher: {e}")
            raise

    #Agent 3
    @agent
    def data_privacy_security_specialist(self) -> Agent:
        try:
            print(f"Creating data_privacy_security_specialist agent...")
            return Agent(
                config=self.agents_config['data_privacy_security_specialist'],
                llm=ollama_llm,
                # tools=[RagSearchTool()],  # Temporarily disabled due to ChromaDB issues
                verbose=True,
            )
        except Exception as e:
            print(f"Error creating data_privacy_security_specialist: {e}")
            raise

    #Agent 4
    @agent
    def risk_report_generator(self) -> Agent:
        try:
            print(f"Creating risk_report_generator agent...")
            return Agent(
                config=self.agents_config['risk_report_generator'],
                llm=ollama_llm,
                verbose=True,
            )
        except Exception as e:
            print(f"Error creating risk_report_generator: {e}")
            raise

    
    @task
    def ai_risk_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['ai_risk_analysis_task'], 
        )

    @task
    def ai_compliance_research_task(self) -> Task:
        return Task(
            config=self.tasks_config['ai_compliance_research_task'], 
        )

    @task
    def data_privacy_security_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_privacy_security_task'], 
        )

    @task
    def risk_report_task(self) -> Task:
        return Task(
            config=self.tasks_config['risk_report_task'], 
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AiLatestDevelopment crew"""
       

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )

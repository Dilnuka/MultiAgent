from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import litellm
import time
import random
from dotenv import load_dotenv
load_dotenv()
try:
    from .tools import RagSearchTool
except Exception:  
    from tools import RagSearchTool



# Configure LiteLLM for LM Studio
# LM Studio runs an OpenAI-compatible API server; we configure litellm to use it.
model_name = os.getenv('MODEL', os.getenv('GEMINI_MODEL', 'lm-studio/llama-3.2-1b-instruct'))
api_base = os.getenv('LMSTUDIO_API_BASE', os.getenv('LITELLM_BASE_URL', 'http://127.0.0.1:1234/v1'))
api_key = os.getenv('LMSTUDIO_API_KEY', os.getenv('LM_STUDIO_API_KEY', os.getenv('GEMINI_API_KEY', 'lm-studio')))

# Expose to environment for other libs that may read them
os.environ['LM_STUDIO_API_BASE'] = api_base
os.environ['LM_STUDIO_API_KEY'] = api_key

# Configure litellm to use lm-studio provider
litellm.custom_llm_provider = 'lm-studio'
litellm.api_base = api_base
litellm.api_key = api_key

# Map lm-studio/ model names to openai/ style for litellm compatibility when needed
if model_name.startswith('lm-studio/'):
    actual_model = model_name.replace('lm-studio/', '')
    final_model = f'openai/{actual_model}'
else:
    final_model = model_name

print(f"Using model: {final_model} with API base: {api_base}")

# Create a shared LLM instance compatible with CrewAI's expected LLM interface
try:
    studio_llm = LLM(
        model=final_model,
        base_url=api_base,
        api_key=api_key,
    )
    print(f"Initialized studio LLM: {final_model}")
except Exception as e:
    print(f"Warning: Failed to initialize LLM with {final_model}: {e}")
    # Try fallback to openai/<model> without lm-studio prefix
    try:
        fallback_model = model_name.split('/')[-1]
        fallback_model = f'openai/{fallback_model}'
        studio_llm = LLM(
            model=fallback_model,
            base_url=api_base,
            api_key=api_key,
        )
        print(f"Initialized fallback studio LLM: {fallback_model}")
    except Exception as e2:
        raise Exception(f"Could not initialize LM Studio LLM: {e}; {e2}")

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
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['ai_risk_assessment_analyst'], # type: ignore[index]
            llm=studio_llm,
            verbose=verbose_flag
        )

    @agent
    def ai_compliance_researcher(self) -> Agent:
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['ai_compliance_researcher'], # type: ignore[index]
            llm=studio_llm,
            tools=[RagSearchTool()],
            verbose=verbose_flag
        )

    @agent
    def data_privacy_security_specialist(self) -> Agent:
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['data_privacy_security_specialist'], # type: ignore[index]
            llm=studio_llm,
            tools=[RagSearchTool()],
            verbose=verbose_flag
        )

    @agent
    def risk_report_generator(self) -> Agent:
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['risk_report_generator'], # type: ignore[index]
            llm=studio_llm,
            verbose=verbose_flag
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
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
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=verbose_flag,
        )

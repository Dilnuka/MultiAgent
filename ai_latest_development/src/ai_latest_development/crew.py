from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import litellm
import time
import random
try:
    from .tools import RagSearchTool
except Exception:  
    from tools import RagSearchTool

# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

class GeminiLLM:
    """Custom Gemini LLM wrapper for CrewAI"""
    
    def __init__(self, model="gemini/gemini-2.0-flash-lite-001", api_key=None):
        self.model = model
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
    def call(self, prompt, **kwargs):
        """Call the Gemini API using litellm"""
        max_retries = int(os.getenv("GEMINI_MAX_RETRIES", 4))
        base_delay = float(os.getenv("GEMINI_BACKOFF_BASE", 1.0))
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                response = litellm.completion(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    api_key=self.api_key,
                    timeout=60,
                    max_retries=0,
                    **kwargs
                )
                return response.choices[0].message.content
            except Exception as e:
                last_err = e
                msg = str(e)
                lower = msg.lower()
                is_503 = ("503" in msg) or ("overloaded" in lower) or ("unavailable" in lower)
                is_429 = ("429" in msg) or ("resource_exhausted" in lower) or ("quota" in lower)
                if attempt < max_retries and (is_503 or is_429):
                    # Respect server-suggested retry delay if present (e.g., "retry in 59s" or RetryInfo)
                    retry_seconds = None
                    # Simple parse: look for 'retry in <number>' or 'retryDelay: "<Ns>"'
                    import re
                    m = re.search(r"retry\s+in\s+(\d+)", lower)
                    if m:
                        retry_seconds = int(m.group(1))
                    else:
                        m = re.search(r"retrydelay\"?[:=]?\s*\"?(\d+)", lower)
                        if m:
                            retry_seconds = int(m.group(1))
                    if retry_seconds is None:
                        # Exponential backoff with jitter
                        retry_seconds = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
                    time.sleep(float(retry_seconds))
                    continue
                break
        raise Exception(f"Error calling Gemini API after {max_retries} attempts: {last_err}")

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
        model_name = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash-lite-001")
        llm = GeminiLLM(
            model=model_name,
            api_key=os.getenv("GEMINI_API_KEY")
        )
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['ai_risk_assessment_analyst'], # type: ignore[index]
            llm=llm,
            verbose=verbose_flag
        )

    @agent
    def ai_compliance_researcher(self) -> Agent:
        model_name = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash-lite-001")
        llm = GeminiLLM(
            model=model_name,
            api_key=os.getenv("GEMINI_API_KEY")
        )
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['ai_compliance_researcher'], # type: ignore[index]
            llm=llm,
            tools=[RagSearchTool()],
            verbose=verbose_flag
        )

    @agent
    def data_privacy_security_specialist(self) -> Agent:
        model_name = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash-lite-001")
        llm = GeminiLLM(
            model=model_name,
            api_key=os.getenv("GEMINI_API_KEY")
        )
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['data_privacy_security_specialist'], # type: ignore[index]
            llm=llm,
            tools=[RagSearchTool()],
            verbose=verbose_flag
        )

    @agent
    def risk_report_generator(self) -> Agent:
        model_name = os.getenv("GEMINI_MODEL", "gemini/gemini-2.0-flash-lite-001")
        llm = GeminiLLM(
            model=model_name,
            api_key=os.getenv("GEMINI_API_KEY")
        )
        verbose_flag = os.getenv("CREW_VERBOSE", "false").lower() in ("1", "true", "yes")
        return Agent(
            config=self.agents_config['risk_report_generator'], # type: ignore[index]
            llm=llm,
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

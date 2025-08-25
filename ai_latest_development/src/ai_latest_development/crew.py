from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import litellm
try:
    from .tools import RagSearchTool
except Exception:  # Allows running as a script without package context
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
        try:
            response = litellm.completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self.api_key,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error calling Gemini API: {e}")

@CrewBase
class AiLatestDevelopment():
    """AiLatestDevelopment crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def ai_risk_assessment_analyst(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['ai_risk_assessment_analyst'], # type: ignore[index]
            llm=llm,
            verbose=True
        )

    @agent
    def ai_compliance_researcher(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['ai_compliance_researcher'], # type: ignore[index]
            llm=llm,
            tools=[RagSearchTool()],
            verbose=True
        )

    @agent
    def data_privacy_security_specialist(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['data_privacy_security_specialist'], # type: ignore[index]
            llm=llm,
            tools=[RagSearchTool()],
            verbose=True
        )

    @agent
    def risk_report_generator(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['risk_report_generator'], # type: ignore[index]
            llm=llm,
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def ai_risk_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['ai_risk_analysis_task'], # type: ignore[index]
        )

    @task
    def ai_compliance_research_task(self) -> Task:
        return Task(
            config=self.tasks_config['ai_compliance_research_task'], # type: ignore[index]
        )

    @task
    def data_privacy_security_task(self) -> Task:
        return Task(
            config=self.tasks_config['data_privacy_security_task'], # type: ignore[index]
        )

    @task
    def risk_report_task(self) -> Task:
        return Task(
            config=self.tasks_config['risk_report_task'], # type: ignore[index]
            output_file='report.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the AiLatestDevelopment crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )

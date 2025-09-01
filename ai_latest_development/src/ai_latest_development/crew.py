from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
import os
import litellm
try:
    from .tools import RagSearchTool
except Exception:  
    from tools import RagSearchTool



#call to the Gemini model using API KEY

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

    #Agent 1
    @agent
    def ai_risk_assessment_analyst(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['ai_risk_assessment_analyst'], 
            llm=llm,
            verbose=True
        )

    #Agent 2
    @agent
    def ai_compliance_researcher(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['ai_compliance_researcher'], 
            llm=llm,
            tools=[RagSearchTool()],
            verbose=True
        )

    #Agent 3
    @agent
    def data_privacy_security_specialist(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['data_privacy_security_specialist'], 
            llm=llm,
            tools=[RagSearchTool()],
            verbose=True
        )

    #Agent 4
    @agent
    def risk_report_generator(self) -> Agent:
        llm = GeminiLLM(
            model="gemini/gemini-2.0-flash-lite-001",
            api_key=os.getenv("GEMINI_API_KEY")
        )
        return Agent(
            config=self.agents_config['risk_report_generator'], 
            llm=llm,
            verbose=True
        )

    
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

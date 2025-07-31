# app/services/enhanced_rag_workflow.py

from typing import Dict, List, Optional, Any, TypedDict
import asyncio
import json
from datetime import datetime
import logging
import uuid

from langgraph.graph import StateGraph, START, END
from app.services.core.agents import (
    SimpleAgent,
    PlanningAgent,
    RetrieverAgent,
    CriticAgent1,
    ReportGeneratorAgent,
)
from app.services.core.enhanced_graph_rag import EnhancedGraphRAG
from app.services.storage.insight_storage import InsightStorage
from app.services.storage.user_memory import UserMemorySystem
from app.services.user_memory import user_memory_service

logger = logging.getLogger(__name__)


class EnhancedWorkflowState(TypedDict):
    """강화된 워크플로우 상태 관리 - LangGraph 호환"""

    query: str
    user_id: str
    session_id: str
    user_context: Dict
    is_simple: bool
    plan: List[str]
    retrieved_data: Dict
    report: str
    is_sufficient: bool
    feedback: str
    graph_context: Dict
    iteration_count: int
    max_iterations: int


class EnhancedRAGWorkflow:
    """
    Graph RAG + 메모리 강화된 Multi-Agent RAG 워크플로우
    """

    def __init__(self):
        # 기존 에이전트들
        self.simple_agent = SimpleAgent()
        self.planning_agent = PlanningAgent()
        self.retriever_agent = RetrieverAgent()
        self.critic_agent = CriticAgent1()
        self.report_generator = ReportGeneratorAgent()

        # 새로운 강화 시스템들
        self.enhanced_graph_rag = EnhancedGraphRAG()
        self.insight_storage = InsightStorage()
        self.user_memory = UserMemorySystem()

        # 워크플로우 그래프 구성
        self._build_workflow()

    def _build_workflow(self):
        """멀티에이전트 워크플로우 그래프 구성"""
        self.workflow = StateGraph(EnhancedWorkflowState)

        # 노드 추가
        self.workflow.add_node("user_context_loader", self.user_context_loader_node)
        self.workflow.add_node("planning_route", self._planning_route)
        self.workflow.add_node("simple_response", self.simple_response_node)
        self.workflow.add_node("planning", self.planning_node)
        self.workflow.add_node("graph_rag_enhancement", self.graph_rag_enhancement_node)
        self.workflow.add_node("retrieval", self.retrieval_node)
        self.workflow.add_node("critic", self.critic_node)
        self.workflow.add_node("report_generation", self.report_generation_node)
        self.workflow.add_node("insight_storage", self.insight_storage_node)
        self.workflow.add_node("memory_update", self.memory_update_node)

        # 시작점 설정
        self.workflow.add_edge(START, "user_context_loader")

        # 사용자 컨텍스트 로딩 후 라우팅
        self.workflow.add_edge("user_context_loader", "planning_route")

        # 라우팅 후 분기
        self.workflow.add_conditional_edges(
            "planning_route",
            self._route_condition,
            {"simple": "simple_response", "complex": "planning"},
        )

        # 간단한 응답 경로
        self.workflow.add_edge("simple_response", "memory_update")

        # 복잡한 분석 경로
        self.workflow.add_edge("planning", "graph_rag_enhancement")
        self.workflow.add_edge("graph_rag_enhancement", "retrieval")
        self.workflow.add_edge("retrieval", "critic")

        # 크리틱 후 조건부 분기
        self.workflow.add_conditional_edges(
            "critic",
            self._critic_condition,
            {"sufficient": "report_generation", "insufficient": "retrieval"},
        )

        # 최종 처리
        self.workflow.add_edge("report_generation", "insight_storage")
        self.workflow.add_edge("insight_storage", "memory_update")
        self.workflow.add_edge("memory_update", END)

        # 워크플로우 컴파일
        self.app = self.workflow.compile()

    async def aprocess(
        self, query: str, user_id: str = "default", session_id: str = None
    ) -> str:
        """비동기 처리 메인 함수"""

        # 세션 ID 생성
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # 초기 상태 설정 (Dictionary 형태)
        initial_state: EnhancedWorkflowState = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "user_context": {},
            "is_simple": False,
            "plan": [],
            "retrieved_data": {},
            "report": "",
            "is_sufficient": False,
            "feedback": "",
            "graph_context": {},
            "iteration_count": 0,
            "max_iterations": 3,
        }

        try:
            # 워크플로우 실행
            result = await self.app.ainvoke(initial_state)

            # 결과 반환
            if result["is_simple"]:
                return result["report"] or "간단한 질문에 대한 응답을 제공했습니다."
            else:
                return result["report"] or "복잡한 분석을 완료했습니다."

        except Exception as e:
            logger.error(f"워크플로우 처리 실패: {e}")
            return f"처리 중 오류가 발생했습니다: {str(e)}"

    async def user_context_loader_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """사용자 컨텍스트 로딩 노드 (새로운 사용자 메모리 서비스 활용)"""
        try:
            # 1. 기존 사용자 메모리에서 컨텍스트 로드
            memory_context = await self.user_memory.get_user_context(
                state["user_id"], state["session_id"]
            )
            
            # 2. 프론트엔드에서 전달받은 사용자 컨텍스트 사용
            frontend_context = state.get("user_context", {})
            
            # 3. 새로운 사용자 메모리 서비스에서 사용자 정보 저장/조회
            user_name = frontend_context.get("user_name", "")
            if user_name and frontend_context:
                # 사용자 프로필 저장
                user_memory_service.save_user_profile(
                    user_id=state["user_id"],
                    user_name=user_name,
                    user_context=frontend_context
                )
            
            # 4. 저장된 사용자 프로필 조회
            stored_profile = user_memory_service.get_user_profile(state["user_id"])
            
            # 5. RDB에서 사용자 프로필 가져오기 (PersonalizedInsightGenerator 활용)
            from app.services.core.personalized_insight_generator import PersonalizedInsightGenerator
            insight_generator = PersonalizedInsightGenerator()
            rdb_profile = insight_generator.get_user_profile_from_db(state["user_id"])
            
            # 6. 통합된 사용자 컨텍스트 생성
            integrated_context = {
                **memory_context,  # 기존 메모리 시스템 데이터
                **frontend_context,  # 프론트엔드에서 전달받은 실시간 데이터
                "rdb_profile": rdb_profile,  # RDB 저장된 프로필 데이터
                "stored_profile": stored_profile,  # 새로운 메모리 서비스에서 조회한 프로필
                "user_name": stored_profile["user_name"] if stored_profile else frontend_context.get("user_name", ""),
                "investment_experience": stored_profile["investment_experience"] if stored_profile else frontend_context.get("investment_experience", ""),
                "risk_tolerance": stored_profile["risk_tolerance"] if stored_profile else frontend_context.get("risk_tolerance", ""),
                "preferred_sectors": stored_profile["preferred_sectors"] if stored_profile else frontend_context.get("preferred_sectors", []),
                "portfolio_count": stored_profile["portfolio_count"] if stored_profile else frontend_context.get("portfolio_count", 0),
                "is_personalized": bool(rdb_profile.get("portfolio", [])),  # 포트폴리오 있으면 개인화됨
            }
            
            # 7. 채팅용 사용자 컨텍스트 생성 (사용자 이름 등 기본 정보 포함)
            user_context_for_chat = user_memory_service.get_user_context_for_chat(state["user_id"])
            integrated_context["chat_context"] = user_context_for_chat
            
            state["user_context"] = integrated_context

            # 8. 최근 인사이트 검색
            recent_insights = await self.insight_storage.search_insights(
                query=state["query"], user_id=state["user_id"], limit=3
            )
            state["user_context"]["recent_insights"] = recent_insights

            profile_name = stored_profile["user_name"] if stored_profile else frontend_context.get('user_name', 'Unknown')
            profile_exp = stored_profile["investment_experience"] if stored_profile else frontend_context.get('investment_experience', 'N/A')
            profile_count = stored_profile["portfolio_count"] if stored_profile else frontend_context.get('portfolio_count', 0)

            logger.info(
                f"사용자 컨텍스트 로딩 완료 - 사용자: {profile_name}, "
                f"경험: {profile_exp}, "
                f"포트폴리오: {profile_count}개"
            )

        except Exception as e:
            logger.error(f"사용자 컨텍스트 로딩 실패: {e}")
            # 최소한 프론트엔드 컨텍스트라도 사용
            state["user_context"] = state.get("user_context", {})

        return state

    async def _planning_route(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """Planning 라우팅 노드"""
        try:
            # LLM 기반 쿼리 분류
            is_simple = await self.simple_agent.is_simple_query(state["query"])
            state["is_simple"] = is_simple

            logger.info(f"쿼리 분류 결과: {'Simple' if is_simple else 'Complex'}")

        except Exception as e:
            logger.error(f"쿼리 분류 실패: {e}")
            state["is_simple"] = False  # 기본값은 복잡한 쿼리

        return state

    def _route_condition(self, state: EnhancedWorkflowState) -> str:
        """라우팅 조건 함수"""
        return "simple" if state["is_simple"] else "complex"

    async def simple_response_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """간단한 응답 노드"""
        try:
            response = await self.simple_agent.generate_simple_response(state["query"])
            state["report"] = response
            logger.info("간단한 응답 생성 완료")

        except Exception as e:
            logger.error(f"간단한 응답 생성 실패: {e}")
            state["report"] = "간단한 질문에 대한 기본 응답을 제공합니다."

        return state

    async def planning_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """계획 수립 노드"""
        try:
            plan = await self.planning_agent.plan(state["query"], state["feedback"])
            state["plan"] = plan
            logger.info(f"계획 수립 완료: {len(plan)}개 하위 쿼리")

        except Exception as e:
            logger.error(f"계획 수립 실패: {e}")
            state["plan"] = [state["query"]]  # 기본값

        return state

    async def graph_rag_enhancement_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """Graph RAG 강화 노드"""
        try:
            # Graph RAG 컨텍스트 생성
            graph_context = await self.enhanced_graph_rag.get_real_time_graph_context(
                state["query"], state["user_context"]
            )
            state["graph_context"] = graph_context

            logger.info(
                f"Graph RAG 컨텍스트 생성: {len(graph_context.get('entities', []))}개 엔티티"
            )

        except Exception as e:
            logger.error(f"Graph RAG 강화 실패: {e}")
            state["graph_context"] = {}

        return state

    async def retrieval_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """데이터 검색 노드"""
        try:
            # Graph RAG 컨텍스트를 포함한 검색
            enhanced_query = state["query"]
            if state["graph_context"].get("entities"):
                enhanced_query += f" (관련 엔티티: {', '.join(state['graph_context']['entities'][:3])})"

            # Plan에서 sub_queries 추출
            if isinstance(state["plan"], list) and len(state["plan"]) > 0:
                # Plan이 문자열 리스트인 경우와 dict 리스트인 경우 모두 처리
                sub_queries = []
                for item in state["plan"]:
                    if isinstance(item, dict):
                        sub_queries.append(item.get("쿼리명", str(item)))
                    else:
                        sub_queries.append(str(item))
            else:
                sub_queries = [enhanced_query]

            # 동기 메서드를 비동기로 실행
            import asyncio

            retrieved_data = await asyncio.to_thread(
                self.retriever_agent.retrieve, sub_queries
            )
            state["retrieved_data"] = retrieved_data

            logger.info("데이터 검색 완료")

        except Exception as e:
            logger.error(f"데이터 검색 실패: {e}")
            state["retrieved_data"] = {}

        return state

    async def critic_node(self, state: EnhancedWorkflowState) -> EnhancedWorkflowState:
        """크리틱 평가 노드"""
        try:
            # CriticAgent1.evaluate는 retrieved_data와 original_query만 받음
            evaluation = await asyncio.to_thread(
                self.critic_agent.evaluate, state["retrieved_data"], state["query"]
            )
            state["is_sufficient"] = evaluation.get("sufficiency", True)
            state["feedback"] = evaluation.get("feedback", "")
            state["iteration_count"] += 1

            logger.info(
                f"크리틱 평가: {'충분' if state['is_sufficient'] else '불충분'}"
            )

        except Exception as e:
            logger.error(f"크리틱 평가 실패: {e}")
            state["is_sufficient"] = True  # 기본값

        return state

    def _critic_condition(self, state: EnhancedWorkflowState) -> str:
        """크리틱 조건 함수"""
        # 최대 반복 횟수 확인
        if state["iteration_count"] >= state["max_iterations"]:
            return "sufficient"

        return "sufficient" if state["is_sufficient"] else "insufficient"

    async def report_generation_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """리포트 생성 노드"""
        try:
            logger.info("🎯 리포트 생성 시작")
            # 컨텍스트를 통합하여 전달
            integrated_context = f"""
# 사용자 질문
{state["query"]}

# 수집된 데이터
{json.dumps(state["retrieved_data"], ensure_ascii=False, indent=2)}

# Graph RAG 컨텍스트
{json.dumps(state["graph_context"], ensure_ascii=False, indent=2)}
"""

            logger.info(f"📝 통합 컨텍스트 길이: {len(integrated_context)}자")
            # ReportGeneratorAgent.generate는 context와 user_context만 받음
            report = await asyncio.to_thread(
                self.report_generator.generate,
                integrated_context,
                state["user_context"],
            )
            state["report"] = report
            logger.info(f"✅ 리포트 생성 완료: {len(report)}자")

        except Exception as e:
            logger.error(f"❌ 리포트 생성 실패: {e}")
            state["report"] = "리포트 생성 중 오류가 발생했습니다."

        return state

    async def insight_storage_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """인사이트 저장 노드"""
        try:
            if state["report"] and not state["is_simple"]:
                # 복잡한 분석 결과만 저장
                insight_id = await self.insight_storage.store_insight(
                    insight_content=state["report"],
                    user_query=state["query"],
                    user_id=state["user_id"],
                    entities=state["graph_context"].get("entities", []),
                    metadata={
                        "graph_rag_used": bool(state["graph_context"]),
                        "data_sources": ["elasticsearch", "neo4j", "real_time"],
                        "confidence_score": 0.8,
                        "workflow_used": True,
                        "iteration_count": state["iteration_count"],
                    },
                )
                logger.info(f"인사이트 저장 완료: {insight_id}")

        except Exception as e:
            logger.error(f"인사이트 저장 실패: {e}")

        return state

    async def memory_update_node(
        self, state: EnhancedWorkflowState
    ) -> EnhancedWorkflowState:
        """메모리 업데이트 노드 (새로운 사용자 메모리 서비스 활용)"""
        try:
            # 기존 메모리 시스템에 저장
            await self.user_memory.save_message(
                user_id=state["user_id"],
                session_id=state["session_id"],
                message_type="user",
                content=state["query"],
                entities=state["graph_context"].get("entities", []),
                intent="investment_query",
            )

            # 시스템 응답 저장
            response_content = (
                state["report"] if not state["is_simple"] else "간단한 응답 제공"
            )
            await self.user_memory.save_message(
                user_id=state["user_id"],
                session_id=state["session_id"],
                message_type="assistant",
                content=response_content,
                entities=state["graph_context"].get("entities", []),
            )
            
            # 새로운 사용자 메모리 서비스에도 대화 기록 저장
            user_memory_service.save_conversation(
                user_id=state["user_id"],
                message=state["query"],
                response=response_content
            )
            
            logger.info(f"메모리 업데이트 완료 - 사용자: {state['user_id']}")

        except Exception as e:
            logger.error(f"메모리 업데이트 실패: {e}")

        return state

    # 편의 메서드들
    async def chat(self, query: str, user_id: str = "default") -> str:
        """채팅 인터페이스"""
        return await self.aprocess(query, user_id)

    async def chat_with_progress(self, query: str, user_id: str = "default", user_context: Dict = None):
        """진행 상황을 스트리밍하는 채팅 인터페이스"""
        # 세션 ID 생성
        session_id = (
            f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        )

        # 초기 상태 설정
        initial_state: EnhancedWorkflowState = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "user_context": user_context or {},
            "is_simple": False,
            "plan": [],
            "retrieved_data": {},
            "report": "",
            "is_sufficient": False,
            "feedback": "",
            "graph_context": {},
            "iteration_count": 0,
            "max_iterations": 3,
        }

        try:
            # 단계별 진행 상황 yield
            yield {
                "status": "processing",
                "step": "context_loading",
                "message": "사용자 컨텍스트를 로딩하고 있습니다...",
            }

            # 사용자 컨텍스트 로딩
            state = await self.user_context_loader_node(initial_state)

            yield {
                "status": "processing",
                "step": "query_classification",
                "message": "질문을 분석하고 있습니다...",
            }

            # 쿼리 분류
            state = await self._planning_route(state)

            if state["is_simple"]:
                yield {
                    "status": "processing",
                    "step": "simple_response",
                    "message": "간단한 응답을 생성하고 있습니다...",
                }
                state = await self.simple_response_node(state)

                yield {
                    "status": "processing",
                    "step": "memory_update",
                    "message": "메모리를 업데이트하고 있습니다...",
                }
                state = await self.memory_update_node(state)

                yield {
                    "status": "completed",
                    "response": state["report"],
                    "message": "응답 생성이 완료되었습니다.",
                }
            else:
                yield {
                    "status": "processing",
                    "step": "planning",
                    "message": "분석 계획을 수립하고 있습니다...",
                }
                state = await self.planning_node(state)

                yield {
                    "status": "processing",
                    "step": "graph_rag",
                    "message": "Graph RAG 컨텍스트를 생성하고 있습니다...",
                    "data": {"plan_count": len(state["plan"])},
                }
                state = await self.graph_rag_enhancement_node(state)

                yield {
                    "status": "processing",
                    "step": "retrieval",
                    "message": "정보를 수집하고 있습니다...",
                }
                state = await self.retrieval_node(state)

                yield {
                    "status": "processing",
                    "step": "evaluation",
                    "message": "수집된 정보를 평가하고 있습니다...",
                }
                state = await self.critic_node(state)

                if (
                    not state["is_sufficient"]
                    and state["iteration_count"] < state["max_iterations"]
                ):
                    yield {
                        "status": "processing",
                        "step": "additional_retrieval",
                        "message": "추가 정보를 수집하고 있습니다...",
                    }
                    state = await self.retrieval_node(state)
                    state = await self.critic_node(state)

                yield {
                    "status": "processing",
                    "step": "report_generation",
                    "message": "투자 인사이트를 생성하고 있습니다...",
                }
                state = await self.report_generation_node(state)

                yield {
                    "status": "processing",
                    "step": "insight_storage",
                    "message": "분석 결과를 저장하고 있습니다...",
                }
                state = await self.insight_storage_node(state)

                yield {
                    "status": "processing",
                    "step": "memory_update",
                    "message": "메모리를 업데이트하고 있습니다...",
                }
                state = await self.memory_update_node(state)

                yield {
                    "status": "completed",
                    "response": state["report"],
                    "message": "분석이 완료되었습니다.",
                }

        except Exception as e:
            logger.error(f"워크플로우 스트리밍 처리 실패: {e}")
            yield {
                "status": "error",
                "error": str(e),
                "message": "처리 중 오류가 발생했습니다.",
            }

    async def get_user_insights(self, user_id: str, limit: int = 10) -> List[Dict]:
        """사용자 인사이트 이력 조회"""
        return await self.insight_storage.get_user_insights(user_id, limit)

    async def get_conversation_history(
        self, user_id: str, session_id: str = None
    ) -> List[Dict]:
        """대화 이력 조회"""
        return await self.user_memory.get_conversation_history(user_id, session_id)

    async def create_user_profile(self, user_data: Dict) -> bool:
        """사용자 프로필 생성"""
        return await self.user_memory.create_user_profile(user_data)

    async def add_user_stock(self, user_id: str, stock_data: Dict) -> bool:
        """사용자 보유 주식 추가"""
        return await self.user_memory.add_holding(user_id, stock_data)

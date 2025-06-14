"""Analytics service for data processing and visualization."""
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio

import pandas as pd
import numpy as np
import networkx as nx
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sqlmodel import Session, select
import structlog

from ..models import Survey, Response, User, SurveyInvitation, AnalyticsSnapshot, Organization
from ..config import settings


logger = structlog.get_logger()


class AnalyticsService:
    """Service for analytics and data visualization."""
    
    def __init__(self, session: Session):
        self.session = session
    
    async def calculate_survey_metrics(
        self,
        survey_id: int,
        include_departments: bool = True
    ) -> Dict[str, Any]:
        """Calculate comprehensive metrics for a survey."""
        survey = self.session.get(Survey, survey_id)
        if not survey:
            raise ValueError("Survey not found")
        
        # Get responses and invitations
        responses = self.session.exec(
            select(Response).where(Response.survey_id == survey_id)
        ).all()
        
        invitations = self.session.exec(
            select(SurveyInvitation).where(SurveyInvitation.survey_id == survey_id)
        ).all()
        
        # Basic metrics
        total_invitations = len(invitations)
        total_responses = len(responses)
        completed_invitations = len([i for i in invitations if i.completed_at])
        opened_invitations = len([i for i in invitations if i.opened_at])
        
        response_rate = (total_responses / total_invitations * 100) if total_invitations > 0 else 0
        completion_rate = (completed_invitations / total_invitations * 100) if total_invitations > 0 else 0
        open_rate = (opened_invitations / total_invitations * 100) if total_invitations > 0 else 0
        
        # Calculate average response time
        response_times = []
        if survey.activated_at:
            for response in responses:
                time_diff = (response.submitted_at - survey.activated_at).total_seconds() / 3600
                response_times.append(time_diff)
        
        avg_response_time = np.mean(response_times) if response_times else 0
        
        # Calculate engagement score based on multiple factors
        engagement_score = self._calculate_engagement_score(
            response_rate, completion_rate, avg_response_time, responses
        )
        
        # Calculate satisfaction scores based on survey type
        satisfaction_scores = self._calculate_satisfaction_scores(survey, responses)
        
        # Generate key insights
        key_insights = self._generate_key_insights(
            survey, response_rate, engagement_score, satisfaction_scores
        )
        
        metrics = {
            "survey_id": survey_id,
            "survey_title": survey.title,
            "survey_type": survey.survey_type,
            "response_rate": round(response_rate, 2),
            "completion_rate": round(completion_rate, 2),
            "open_rate": round(open_rate, 2),
            "avg_response_time": round(avg_response_time, 2),
            "engagement_score": round(engagement_score, 2),
            "total_responses": total_responses,
            "total_invitations": total_invitations,
            "key_insights": key_insights,
            **satisfaction_scores
        }
        
        # Add department breakdown if requested
        if include_departments:
            metrics["metrics_by_department"] = await self._calculate_department_metrics(
                survey_id, responses, invitations
            )
        
        return metrics
    
    def _calculate_engagement_score(
        self,
        response_rate: float,
        completion_rate: float,
        avg_response_time: float,
        responses: List[Response]
    ) -> float:
        """Calculate overall engagement score."""
        # Base score from response rate (0-40 points)
        response_score = min(response_rate * 0.4, 40)
        
        # Completion quality score (0-30 points)
        completion_score = min(completion_rate * 0.3, 30)
        
        # Response speed score (0-20 points)
        # Faster responses (within 24 hours) get higher scores
        if avg_response_time <= 24:
            speed_score = 20
        elif avg_response_time <= 72:
            speed_score = 15
        elif avg_response_time <= 168:  # 1 week
            speed_score = 10
        else:
            speed_score = 5
        
        # Response quality score (0-10 points)
        # Based on answer completeness and variety
        quality_score = self._calculate_response_quality_score(responses)
        
        total_score = response_score + completion_score + speed_score + quality_score
        return min(total_score, 100)  # Cap at 100
    
    def _calculate_response_quality_score(self, responses: List[Response]) -> float:
        """Calculate response quality score based on completeness."""
        if not responses:
            return 0
        
        quality_scores = []
        for response in responses:
            answers = response.answers
            
            # Count non-empty answers
            non_empty_answers = sum(1 for answer in answers.values() if answer not in [None, "", []])
            total_questions = len(answers)
            
            if total_questions > 0:
                completeness = non_empty_answers / total_questions
                quality_scores.append(completeness)
        
        avg_quality = np.mean(quality_scores) if quality_scores else 0
        return avg_quality * 10  # Scale to 0-10
    
    def _calculate_satisfaction_scores(self, survey: Survey, responses: List[Response]) -> Dict[str, float]:
        """Calculate satisfaction scores based on survey type."""
        scores = {}
        
        if survey.survey_type == "enps":
            scores["nps_score"] = self._calculate_nps_score(responses)
        
        # Calculate general satisfaction if satisfaction questions exist
        satisfaction_score = self._calculate_general_satisfaction(responses)
        if satisfaction_score is not None:
            scores["satisfaction_score"] = satisfaction_score
        
        return scores
    
    def _calculate_nps_score(self, responses: List[Response]) -> float:
        """Calculate Net Promoter Score."""
        nps_values = []
        
        for response in responses:
            # Look for NPS question (usually asks about recommendation likelihood)
            for question_id, answer in response.answers.items():
                if "recommend" in question_id.lower() or "nps" in question_id.lower():
                    if isinstance(answer, (int, float)) and 0 <= answer <= 10:
                        nps_values.append(answer)
                    break
        
        if not nps_values:
            return 0
        
        promoters = len([score for score in nps_values if score >= 9])
        detractors = len([score for score in nps_values if score <= 6])
        total = len(nps_values)
        
        nps = ((promoters - detractors) / total) * 100 if total > 0 else 0
        return round(nps, 2)
    
    def _calculate_general_satisfaction(self, responses: List[Response]) -> Optional[float]:
        """Calculate general satisfaction score."""
        satisfaction_values = []
        
        for response in responses:
            for question_id, answer in response.answers.items():
                if any(keyword in question_id.lower() for keyword in ["satisfaction", "happy", "satisfied"]):
                    if isinstance(answer, (int, float)):
                        satisfaction_values.append(answer)
                    break
        
        if not satisfaction_values:
            return None
        
        return round(np.mean(satisfaction_values), 2)
    
    def _generate_key_insights(
        self,
        survey: Survey,
        response_rate: float,
        engagement_score: float,
        satisfaction_scores: Dict[str, float]
    ) -> List[str]:
        """Generate key insights based on metrics."""
        insights = []
        
        # Response rate insights
        if response_rate >= 80:
            insights.append("Excellent response rate indicates high team engagement")
        elif response_rate >= 60:
            insights.append("Good response rate shows team is generally engaged")
        elif response_rate >= 40:
            insights.append("Moderate response rate suggests room for improvement in engagement")
        else:
            insights.append("Low response rate indicates potential engagement issues")
        
        # Engagement insights
        if engagement_score >= 80:
            insights.append("High engagement score indicates strong survey participation quality")
        elif engagement_score < 50:
            insights.append("Low engagement score suggests need for better survey design or timing")
        
        # NPS insights
        if "nps_score" in satisfaction_scores:
            nps = satisfaction_scores["nps_score"]
            if nps >= 50:
                insights.append("Excellent NPS score shows strong team loyalty")
            elif nps >= 0:
                insights.append("Positive NPS score indicates generally satisfied team")
            else:
                insights.append("Negative NPS score suggests significant satisfaction issues")
        
        # Survey type specific insights
        if survey.survey_type == "sociometry":
            insights.append("Sociometric data can reveal team communication patterns and influence networks")
        
        return insights
    
    async def _calculate_department_metrics(
        self,
        survey_id: int,
        responses: List[Response],
        invitations: List[SurveyInvitation]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate metrics broken down by department."""
        # Get respondent departments
        respondent_ids = [r.respondent_id for r in responses if r.respondent_id]
        if not respondent_ids:
            return {}
        
        users = self.session.exec(
            select(User).where(User.id.in_(respondent_ids))
        ).all()
        
        user_departments = {user.id: user.department or "Unassigned" for user in users}
        
        # Group responses by department
        dept_responses = {}
        for response in responses:
            if response.respondent_id in user_departments:
                dept = user_departments[response.respondent_id]
                if dept not in dept_responses:
                    dept_responses[dept] = []
                dept_responses[dept].append(response)
        
        # Group invitations by department
        invitation_user_ids = [i.respondent_id for i in invitations if i.respondent_id]
        invitation_users = self.session.exec(
            select(User).where(User.id.in_(invitation_user_ids))
        ).all()
        
        invitation_departments = {user.id: user.department or "Unassigned" for user in invitation_users}
        
        dept_invitations = {}
        for invitation in invitations:
            if invitation.respondent_id in invitation_departments:
                dept = invitation_departments[invitation.respondent_id]
                if dept not in dept_invitations:
                    dept_invitations[dept] = []
                dept_invitations[dept].append(invitation)
        
        # Calculate metrics for each department
        dept_metrics = {}
        for dept in set(list(dept_responses.keys()) + list(dept_invitations.keys())):
            dept_resp = dept_responses.get(dept, [])
            dept_inv = dept_invitations.get(dept, [])
            
            response_count = len(dept_resp)
            invitation_count = len(dept_inv)
            
            response_rate = (response_count / invitation_count * 100) if invitation_count > 0 else 0
            
            dept_metrics[dept] = {
                "response_rate": round(response_rate, 2),
                "total_responses": response_count,
                "total_invitations": invitation_count
            }
        
        return dept_metrics
    
    async def generate_network_visualization(
        self,
        survey_id: int,
        include_weights: bool = True,
        min_connection_strength: float = 0.1
    ) -> Dict[str, Any]:
        """Generate network visualization data for sociometric analysis."""
        survey = self.session.get(Survey, survey_id)
        if not survey:
            raise ValueError("Survey not found")
        
        if survey.survey_type not in ["sociometry", "team_dynamics"]:
            raise ValueError("Network analysis not available for this survey type")
        
        # Get responses
        responses = self.session.exec(
            select(Response).where(Response.survey_id == survey_id)
        ).all()
        
        if not responses:
            return {"nodes": [], "links": [], "metadata": {"message": "No responses available"}}
        
        # Get respondent information
        respondent_ids = [r.respondent_id for r in responses if r.respondent_id]
        users = self.session.exec(
            select(User).where(User.id.in_(respondent_ids))
        ).all()
        
        user_map = {user.id: user for user in users}
        
        # Build network graph
        G = nx.Graph()
        
        # Add nodes
        for user in users:
            G.add_node(
                str(user.id),
                name=f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email,
                department=user.department,
                position=user.position
            )
        
        # Analyze responses to create connections
        connections = self._analyze_sociometric_connections(responses, user_map)
        
        # Add edges
        for (source, target), weight in connections.items():
            if weight >= min_connection_strength:
                G.add_edge(source, target, weight=weight)
        
        # Calculate network metrics
        centrality_scores = nx.betweenness_centrality(G)
        eigenvector_scores = nx.eigenvector_centrality(G, max_iter=1000)
        
        # Create nodes data
        nodes = []
        for node_id in G.nodes():
            node_data = G.nodes[node_id]
            
            # Determine node group based on centrality
            centrality = centrality_scores.get(node_id, 0)
            if centrality > 0.1:
                group = "high_influence"
            elif centrality > 0.05:
                group = "medium_influence"
            else:
                group = "low_influence"
            
            nodes.append({
                "id": node_id,
                "name": node_data["name"],
                "group": group,
                "department": node_data.get("department"),
                "position": node_data.get("position"),
                "centrality_score": round(centrality, 3),
                "influence_score": round(eigenvector_scores.get(node_id, 0), 3)
            })
        
        # Create links data
        links = []
        for source, target in G.edges():
            weight = G.edges[source, target]["weight"]
            
            # Determine relationship strength
            if weight >= 0.7:
                strength = "strong"
            elif weight >= 0.4:
                strength = "medium"
            else:
                strength = "weak"
            
            links.append({
                "source": source,
                "target": target,
                "weight": round(weight, 3),
                "strength": strength
            })
        
        # Calculate network metadata
        metadata = {
            "total_nodes": len(nodes),
            "total_connections": len(links),
            "network_density": round(nx.density(G), 3),
            "avg_clustering": round(nx.average_clustering(G), 3),
            "connected_components": nx.number_connected_components(G),
            "analysis_date": datetime.utcnow().isoformat()
        }
        
        return {
            "nodes": nodes,
            "links": links,
            "metadata": metadata
        }
    
    def _analyze_sociometric_connections(
        self,
        responses: List[Response],
        user_map: Dict[int, User]
    ) -> Dict[Tuple[str, str], float]:
        """Analyze responses to determine connections between team members."""
        connections = {}
        
        for response in responses:
            if not response.respondent_id:
                continue
                
            respondent_id = str(response.respondent_id)
            
            # Analyze answers for mentions of other team members
            for question_id, answer in response.answers.items():
                if isinstance(answer, dict) and "selections" in answer:
                    # Handle sociometric questions with multiple selections
                    selections = answer["selections"]
                    if isinstance(selections, list):
                        for selection in selections:
                            if isinstance(selection, dict) and "user_id" in selection:
                                target_id = str(selection["user_id"])
                                weight = selection.get("weight", 1.0)
                                
                                if target_id != respondent_id:  # No self-connections
                                    connection_key = tuple(sorted([respondent_id, target_id]))
                                    connections[connection_key] = connections.get(connection_key, 0) + weight
                
                elif isinstance(answer, list):
                    # Handle list of user IDs
                    for user_id in answer:
                        if isinstance(user_id, (int, str)):
                            target_id = str(user_id)
                            if target_id != respondent_id:
                                connection_key = tuple(sorted([respondent_id, target_id]))
                                connections[connection_key] = connections.get(connection_key, 0) + 0.5
        
        # Normalize connection weights
        if connections:
            max_weight = max(connections.values())
            connections = {k: v / max_weight for k, v in connections.items()}
        
        return connections
    
    async def analyze_team_dynamics(self, survey_id: int) -> Dict[str, Any]:
        """Analyze team dynamics and collaboration patterns."""
        survey = self.session.get(Survey, survey_id)
        if not survey:
            raise ValueError("Survey not found")
        
        # Get network data
        network_data = await self.generate_network_visualization(survey_id)
        
        if not network_data["nodes"]:
            return {"error": "No data available for analysis"}
        
        # Calculate team cohesion score
        metadata = network_data["metadata"]
        team_cohesion_score = self._calculate_team_cohesion(metadata)
        
        # Analyze communication effectiveness
        communication_effectiveness = self._analyze_communication_patterns(network_data)
        
        # Calculate collaboration index
        collaboration_index = self._calculate_collaboration_index(network_data)
        
        # Identify leadership influence
        leadership_influence = self._identify_leadership_influence(network_data["nodes"])
        
        # Analyze department connectivity
        department_connectivity = self._analyze_department_connectivity(network_data)
        
        # Identify isolated members and key connectors
        isolated_members = self._identify_isolated_members(network_data)
        key_connectors = self._identify_key_connectors(network_data["nodes"])
        
        # Generate recommendations
        recommendations = self._generate_team_recommendations(
            team_cohesion_score, communication_effectiveness, isolated_members
        )
        
        return {
            "survey_id": survey_id,
            "team_cohesion_score": round(team_cohesion_score, 2),
            "communication_effectiveness": round(communication_effectiveness, 2),
            "collaboration_index": round(collaboration_index, 2),
            "leadership_influence": leadership_influence,
            "department_connectivity": department_connectivity,
            "isolated_members": isolated_members,
            "key_connectors": key_connectors,
            "recommendations": recommendations
        }
    
    def _calculate_team_cohesion(self, metadata: Dict[str, Any]) -> float:
        """Calculate team cohesion score based on network metrics."""
        density = metadata.get("network_density", 0)
        clustering = metadata.get("avg_clustering", 0)
        components = metadata.get("connected_components", 1)
        
        # Higher density and clustering, fewer components = higher cohesion
        cohesion_score = (density * 50) + (clustering * 30) + (20 / components)
        return min(cohesion_score, 100)
    
    def _analyze_communication_patterns(self, network_data: Dict[str, Any]) -> float:
        """Analyze communication effectiveness based on network structure."""
        nodes = network_data["nodes"]
        links = network_data["links"]
        
        if not nodes:
            return 0
        
        # Calculate average connection strength
        if links:
            avg_strength = np.mean([link["weight"] for link in links])
            strong_connections = len([link for link in links if link["strength"] == "strong"])
            total_connections = len(links)
            
            # Communication effectiveness based on connection quality
            effectiveness = (avg_strength * 60) + ((strong_connections / total_connections) * 40)
        else:
            effectiveness = 0
        
        return min(effectiveness, 100)
    
    def _calculate_collaboration_index(self, network_data: Dict[str, Any]) -> float:
        """Calculate collaboration index based on cross-department connections."""
        nodes = network_data["nodes"]
        links = network_data["links"]
        
        if not nodes or not links:
            return 0
        
        # Create department mapping
        node_departments = {node["id"]: node.get("department") for node in nodes}
        
        # Count cross-department connections
        cross_dept_connections = 0
        total_connections = len(links)
        
        for link in links:
            source_dept = node_departments.get(link["source"])
            target_dept = node_departments.get(link["target"])
            
            if source_dept and target_dept and source_dept != target_dept:
                cross_dept_connections += 1
        
        # Collaboration index as percentage of cross-department connections
        if total_connections > 0:
            collaboration_index = (cross_dept_connections / total_connections) * 100
        else:
            collaboration_index = 0
        
        return collaboration_index
    
    def _identify_leadership_influence(self, nodes: List[Dict[str, Any]]) -> Dict[str, float]:
        """Identify leadership influence patterns."""
        leadership_scores = {}
        
        for node in nodes:
            name = node["name"]
            centrality = node.get("centrality_score", 0)
            influence = node.get("influence_score", 0)
            
            # Combined leadership score
            leadership_score = (centrality * 0.6) + (influence * 0.4)
            leadership_scores[name] = round(leadership_score, 3)
        
        # Return top 5 leaders
        sorted_leaders = sorted(leadership_scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_leaders[:5])
    
    def _analyze_department_connectivity(self, network_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze connectivity within and between departments."""
        nodes = network_data["nodes"]
        links = network_data["links"]
        
        if not nodes:
            return {}
        
        # Group nodes by department
        departments = {}
        for node in nodes:
            dept = node.get("department", "Unassigned")
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(node["id"])
        
        # Calculate connectivity scores for each department
        connectivity_scores = {}
        for dept, node_ids in departments.items():
            if len(node_ids) < 2:
                connectivity_scores[dept] = 0
                continue
            
            # Count internal connections
            internal_connections = 0
            possible_connections = len(node_ids) * (len(node_ids) - 1) // 2
            
            for link in links:
                if link["source"] in node_ids and link["target"] in node_ids:
                    internal_connections += 1
            
            # Connectivity as percentage of possible connections
            if possible_connections > 0:
                connectivity = (internal_connections / possible_connections) * 100
            else:
                connectivity = 0
            
            connectivity_scores[dept] = round(connectivity, 2)
        
        return connectivity_scores
    
    def _identify_isolated_members(self, network_data: Dict[str, Any]) -> List[str]:
        """Identify team members with few connections."""
        nodes = network_data["nodes"]
        links = network_data["links"]
        
        # Count connections for each node
        connection_counts = {node["id"]: 0 for node in nodes}
        
        for link in links:
            connection_counts[link["source"]] += 1
            connection_counts[link["target"]] += 1
        
        # Identify isolated members (fewer than 2 connections)
        isolated = []
        for node in nodes:
            if connection_counts[node["id"]] < 2:
                isolated.append(node["name"])
        
        return isolated
    
    def _identify_key_connectors(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Identify key connectors based on centrality scores."""
        # Sort by centrality score
        sorted_nodes = sorted(nodes, key=lambda x: x.get("centrality_score", 0), reverse=True)
        
        # Return top connectors (with centrality > 0.05)
        key_connectors = []
        for node in sorted_nodes:
            if node.get("centrality_score", 0) > 0.05:
                key_connectors.append(node["name"])
        
        return key_connectors[:5]  # Top 5
    
    def _generate_team_recommendations(
        self,
        cohesion_score: float,
        communication_effectiveness: float,
        isolated_members: List[str]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        if cohesion_score < 50:
            recommendations.append("Consider team building activities to improve overall cohesion")
        
        if communication_effectiveness < 60:
            recommendations.append("Implement regular communication channels and feedback loops")
        
        if len(isolated_members) > 0:
            recommendations.append(f"Focus on integrating isolated team members: {', '.join(isolated_members[:3])}")
        
        if cohesion_score > 80:
            recommendations.append("Strong team cohesion detected - maintain current collaboration practices")
        
        recommendations.append("Schedule regular check-ins to monitor team dynamics")
        
        return recommendations
    
    async def generate_ai_insights(
        self,
        survey_id: int,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Generate AI-powered insights using OpenAI."""
        # Check for cached insights
        if not force_regenerate:
            cached_insights = self.session.exec(
                select(AnalyticsSnapshot).where(
                    AnalyticsSnapshot.survey_id == survey_id,
                    AnalyticsSnapshot.snapshot_type == "insights",
                    AnalyticsSnapshot.expires_at > datetime.utcnow()
                )
            ).first()
            
            if cached_insights:
                return cached_insights.data
        
        # Get survey data
        metrics = await self.calculate_survey_metrics(survey_id)
        network_data = await self.generate_network_visualization(survey_id)
        team_dynamics = await self.analyze_team_dynamics(survey_id)
        
        # Prepare data for AI analysis
        analysis_data = {
            "metrics": metrics,
            "network_summary": {
                "total_nodes": network_data["metadata"].get("total_nodes", 0),
                "network_density": network_data["metadata"].get("network_density", 0),
                "connected_components": network_data["metadata"].get("connected_components", 0)
            },
            "team_dynamics": team_dynamics
        }
        
        try:
            # Generate insights using OpenAI
            insights = await self._call_openai_for_insights(analysis_data)
            
            # Cache insights for 24 hours
            snapshot = AnalyticsSnapshot(
                survey_id=survey_id,
                snapshot_type="insights",
                data=insights,
                expires_at=datetime.utcnow() + timedelta(hours=24)
            )
            
            self.session.add(snapshot)
            self.session.commit()
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate AI insights: {str(e)}")
            # Return fallback insights
            return self._generate_fallback_insights(analysis_data)
    
    async def _call_openai_for_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Call OpenAI API to generate insights."""
        import openai
        
        openai.api_key = settings.openai_api_key
        
        prompt = f"""
        Analyze the following workplace survey data and provide actionable insights:
        
        Survey Metrics:
        - Response Rate: {data['metrics'].get('response_rate', 0)}%
        - Engagement Score: {data['metrics'].get('engagement_score', 0)}
        - Team Size: {data['network_summary'].get('total_nodes', 0)}
        - Network Density: {data['network_summary'].get('network_density', 0)}
        
        Team Dynamics:
        - Team Cohesion: {data['team_dynamics'].get('team_cohesion_score', 0)}
        - Communication Effectiveness: {data['team_dynamics'].get('communication_effectiveness', 0)}
        - Collaboration Index: {data['team_dynamics'].get('collaboration_index', 0)}
        
        Please provide:
        1. 3-5 key insights about team health
        2. Specific recommendations for improvement
        3. Potential risks or areas of concern
        4. Positive aspects to celebrate
        
        Format as JSON with keys: insights, recommendations, risks, positives
        """
        
        response = await openai.ChatCompletion.acreate(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are an expert organizational psychologist analyzing workplace data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Parse response
        content = response.choices[0].message.content
        
        try:
            insights = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            insights = {
                "insights": [content[:200] + "..."],
                "recommendations": ["Review the detailed analysis for specific recommendations"],
                "risks": ["Unable to identify specific risks"],
                "positives": ["Survey completion shows team engagement"]
            }
        
        return insights
    
    def _generate_fallback_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback insights when AI is unavailable."""
        metrics = data["metrics"]
        team_dynamics = data["team_dynamics"]
        
        insights = []
        recommendations = []
        risks = []
        positives = []
        
        # Response rate analysis
        response_rate = metrics.get("response_rate", 0)
        if response_rate >= 70:
            positives.append("High response rate indicates strong team engagement")
        elif response_rate < 40:
            risks.append("Low response rate may indicate disengagement")
            recommendations.append("Investigate barriers to survey participation")
        
        # Team cohesion analysis
        cohesion = team_dynamics.get("team_cohesion_score", 0)
        if cohesion >= 70:
            positives.append("Strong team cohesion detected")
        elif cohesion < 50:
            risks.append("Low team cohesion may affect collaboration")
            recommendations.append("Implement team building initiatives")
        
        # Communication analysis
        communication = team_dynamics.get("communication_effectiveness", 0)
        if communication < 60:
            risks.append("Communication effectiveness could be improved")
            recommendations.append("Establish regular communication channels")
        
        # General insights
        insights.append("Survey data reveals key patterns in team dynamics")
        insights.append("Network analysis shows collaboration opportunities")
        
        return {
            "insights": insights,
            "recommendations": recommendations,
            "risks": risks,
            "positives": positives,
            "generated_at": datetime.utcnow().isoformat(),
            "source": "automated_analysis"
        }
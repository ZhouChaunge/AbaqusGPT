"""
Domain Expert Skill | 领域专家技能
====================================

Domain-specific knowledge and Q&A for various engineering fields.
各工程领域的专业知识问答。
"""

from typing import Any, Dict, List, Optional

from ...knowledge.domains import get_domain_knowledge
from ...llm.client import get_llm_client
from ..base import Skill, SkillMetadata


class DomainExpertSkill(Skill):
    """
    Skill for domain-specific knowledge and Q&A.
    领域特定知识问答的技能。
    """

    # Domain system prompts | 领域系统提示
    DOMAIN_PROMPTS = {
        "geotechnical": """你是一位岩土工程有限元分析专家，精通：
- 本构模型：Mohr-Coulomb、Drucker-Prager、修正剑桥模型 (Cam-Clay)、Hoek-Brown
- 土-结构相互作用 (SSI)
- 渗流-应力耦合分析
- 隧道开挖模拟（应力释放法、刚度折减法）
- 基础承载力分析
- 边坡稳定性分析
- 初始地应力平衡""",

        "structural": """你是一位结构工程有限元分析专家，精通：
- 混凝土损伤塑性模型 (CDP)
- 钢筋混凝土建模（嵌入式钢筋、桁架单元）
- 预应力混凝土分析
- 地震响应分析（时程分析、反应谱分析）
- 连续倒塌分析
- 钢结构连接节点分析
- 混凝土开裂和破坏模拟""",

        "mechanical": """你是一位机械工程有限元分析专家，精通：
- 接触分析（面-面接触、自接触、通用接触）
- 摩擦模型（库仑摩擦、指数摩擦）
- 齿轮、轴承、螺栓连接建模
- 过盈配合分析
- 疲劳分析
- 制造工艺仿真（成形、冲压）
- 装配体分析""",

        "thermal": """你是一位热分析有限元专家，精通：
- 传热分析（传导、对流、辐射）
- 热-结构耦合分析
- 瞬态热分析
- 相变问题
- 焊接仿真（热源模型、残余应力）
- 热循环和热疲劳
- 温度边界条件设置""",

        "impact": """你是一位冲击动力学有限元分析专家，精通：
- Abaqus/Explicit 求解器
- 高应变率材料模型 (Johnson-Cook)
- 碰撞和撞击分析
- 穿甲模拟
- 爆炸和冲击波
- 材料失效和删除
- 质量缩放和时间步控制
- 沙漏控制""",

        "composite": """你是一位复合材料有限元分析专家，精通：
- 层合板理论和建模
- 复合材料失效准则 (Hashin, Puck, LaRC)
- 渐进损伤分析
- 分层 (Delamination) 模拟
- 内聚力单元 (Cohesive Elements)
- VCCT 方法
- 复合材料制造仿真（固化、残余应力）""",

        "biomechanics": """你是一位生物力学有限元分析专家，精通：
- 软组织超弹性模型 (Ogden, Mooney-Rivlin, Yeoh)
- 骨骼材料建模（各向异性、孔隙弹性）
- 植入物-骨骼界面分析
- 血管力学
- 肌肉骨骼系统建模
- 医疗器械仿真
- 患者特异性建模""",

        "general": """你是一位通用有限元分析专家，精通 Abaqus 的各种功能：
- 静力分析、动力分析、热分析
- 接触、材料非线性、几何非线性
- 网格划分、后处理
- 常见问题诊断和解决""",
    }

    def __init__(self, metadata: Optional[SkillMetadata] = None):
        super().__init__(metadata)
        self.llm = get_llm_client()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute domain expert Q&A.
        执行领域专家问答。

        Args:
            context: Query context
                - question: User's question (required)
                - domain: Specific domain to focus on
                - history: Conversation history

        Returns:
            Answer and related information
        """
        question = context.get("question")
        if not question:
            return {
                "status": "error",
                "message": "question is required",
            }

        domain = context.get("domain", "general")
        context.get("history", [])

        # Build system prompt
        system_prompt = self._build_system_prompt(domain)

        # Get relevant domain knowledge
        domain_knowledge = get_domain_knowledge(domain, question)

        # Build context
        context_str = ""
        if domain_knowledge:
            context_str = f"\n\n相关知识库内容：\n{domain_knowledge}\n\n"

        # Format question with context
        full_question = f"{context_str}用户问题：{question}" if context_str else question

        # Generate answer
        answer = self.llm.chat(
            full_question,
            system_prompt=system_prompt,
        )

        # Extract references and code examples
        references = self._extract_references(answer)
        code_examples = self._extract_code_examples(answer)

        return {
            "status": "success",
            "domain": domain,
            "question": question,
            "answer": answer,
            "references": references,
            "code_examples": code_examples,
            "follow_up_questions": self._generate_follow_ups(question, domain),
        }

    def _build_system_prompt(self, domain: str) -> str:
        """Build the system prompt with domain expertise."""
        base_prompt = "你是 AbaqusGPT，一个专业的 Abaqus 有限元分析 AI 助手。\n\n"

        domain_prompt = self.DOMAIN_PROMPTS.get(domain, self.DOMAIN_PROMPTS["general"])

        guidelines = """

回答指南：
1. 提供准确的技术答案，引用 Abaqus 文档
2. 给出具体的关键字和语法示例
3. 说明常见陷阱和最佳实践
4. 如果问题超出你的知识范围，诚实说明

请用中文回答，除非用户使用英文提问。"""

        return base_prompt + domain_prompt + guidelines

    def _extract_references(self, answer: str) -> List[str]:
        """Extract documentation references from answer."""
        references = []

        # Look for Abaqus documentation patterns
        import re
        patterns = [
            r"Abaqus [\w\s]+ Guide [\d.]+",
            r"Section [\d.]+",
            r"\*[\w]+",  # Abaqus keywords
        ]

        for pattern in patterns:
            matches = re.findall(pattern, answer)
            references.extend(matches)

        return list(set(references))[:10]

    def _extract_code_examples(self, answer: str) -> List[Dict[str, str]]:
        """Extract code examples from answer."""
        examples = []

        # Look for code blocks
        import re
        code_pattern = r"```(\w*)\n(.*?)```"
        matches = re.findall(code_pattern, answer, re.DOTALL)

        for lang, code in matches:
            examples.append({
                "language": lang or "text",
                "code": code.strip(),
            })

        return examples

    def _generate_follow_ups(self, question: str, domain: str) -> List[str]:
        """Generate follow-up questions."""
        # Simple heuristic-based follow-ups
        follow_ups = []

        if "收敛" in question or "convergence" in question.lower():
            follow_ups.append("如何诊断具体的收敛问题？")

        if "单元" in question or "element" in question.lower():
            follow_ups.append("不同单元类型之间有什么区别？")

        if "接触" in question or "contact" in question.lower():
            follow_ups.append("如何调整接触参数以改善收敛性？")

        return follow_ups[:3]

    def list_domains(self) -> Dict[str, str]:
        """List available domains with descriptions."""
        return {
            "geotechnical": "岩土工程",
            "structural": "结构工程",
            "mechanical": "机械工程",
            "thermal": "热分析",
            "impact": "冲击动力学",
            "composite": "复合材料",
            "biomechanics": "生物力学",
            "general": "通用分析",
        }


def create_domain_expert(domain: str = "general") -> DomainExpertSkill:
    """Factory function to create a DomainExpertSkill instance."""
    metadata = SkillMetadata(
        name="domain-expert",
        version="1.0.0",
        description="Domain-specific knowledge and Q&A for various engineering fields",
        description_cn="各工程领域的专业知识问答",
        triggers=["ask", "question", "what", "how", "why", "问", "怎么", "为什么"],
    )
    return DomainExpertSkill(metadata)

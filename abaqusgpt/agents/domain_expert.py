"""DomainExpert - Domain-specific Abaqus expert agent."""

from typing import Optional, List

from ..llm.client import get_llm_client
from ..knowledge.domains import get_domain_knowledge


class DomainExpert:
    """Agent with specialized domain knowledge."""
    
    DOMAIN_PROMPTS = {
        "general": """你是一位通用 Abaqus 有限元分析专家，精通：
- Abaqus/CAE 建模和网格划分
- Abaqus/Standard 和 Abaqus/Explicit 求解器
- 各类材料模型和本构关系
- 边界条件和载荷定义
- 接触和相互作用设置
- 收敛问题诊断和解决
- Python 脚本自动化""",

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
        
        "electromagnetic": """你是一位电磁分析有限元专家，精通：
- 电磁-热耦合分析
- 感应加热仿真
- 电磁力计算
- 涡流分析
- 多物理场耦合
- 压电材料建模""",
    }
    
    def __init__(self, domain: str, model: str = None):
        """
        Initialize domain expert.
        
        Args:
            domain: Engineering domain (geotechnical, structural, general, etc.)
            model: LLM model to use
        """
        self.domain = domain
        self.llm = get_llm_client(model=model)
        
        if domain not in self.DOMAIN_PROMPTS:
            raise ValueError(f"Unknown domain: {domain}")
        
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with domain expertise."""
        base_prompt = """你是 AbaqusGPT，一个专业的 Abaqus 有限元分析 AI 助手。

"""
        domain_prompt = self.DOMAIN_PROMPTS.get(self.domain, "")
        
        guidelines = """

回答指南：
1. 提供准确的技术答案，引用 Abaqus 文档
2. 给出具体的关键字和语法示例
3. 说明常见陷阱和最佳实践
4. 如果问题超出你的知识范围，诚实说明

请用中文回答，除非用户使用英文提问。"""
        
        return base_prompt + domain_prompt + guidelines
    
    def answer(
        self, 
        question: str, 
        history: Optional[List[dict]] = None
    ) -> str:
        """
        Answer a domain-specific question.
        
        Args:
            question: User's question
            history: Conversation history
            
        Returns:
            Expert answer
        """
        # Get relevant domain knowledge
        domain_knowledge = get_domain_knowledge(self.domain, question)
        
        # Build context
        context = ""
        if domain_knowledge:
            context = f"\n\n相关知识库内容：\n{domain_knowledge}\n\n"
        
        # Limit history to last 6 messages
        limited_history = history[-6:] if history else None
        
        # Add current question
        full_question = f"{context}用户问题：{question}" if context else question
        
        response = self.llm.chat(
            full_question,
            system_prompt=self.system_prompt,
            history=limited_history,
        )
        
        return response

"""Domain-specific knowledge retrieval."""

from typing import Optional

# Domain knowledge templates (will be expanded with RAG)
DOMAIN_KNOWLEDGE = {
    "geotechnical": {
        "初始地应力": """在 Abaqus 中设置初始地应力的方法：

1. **使用 *INITIAL CONDITIONS, TYPE=STRESS**
```
*INITIAL CONDITIONS, TYPE=STRESS
element_set, sigma_11, sigma_22, sigma_33, sigma_12, sigma_13, sigma_23
```

2. **地应力平衡步骤**
```
*STEP, NAME=Geostatic
*GEOSTATIC
*DLOAD
ALL, GRAV, 9.81, 0., -1., 0.
*END STEP
```

3. **注意事项**：
- 确保初始应力与重力载荷平衡
- K0 = sigma_h / sigma_v (静止土压力系数)
- 使用 *GEOSTATIC 步骤可自动平衡
""",

        "本构模型": """常用岩土本构模型：

1. **Mohr-Coulomb**
```
*MATERIAL, NAME=SOIL
*ELASTIC
20000., 0.3
*MOHR COULOMB
30., 0.
*MOHR COULOMB HARDENING
0., 0.
100., 0.1
```

2. **Drucker-Prager**
```
*DRUCKER PRAGER
30., 1., 0.
*DRUCKER PRAGER HARDENING
100., 0.
200., 0.1
```

3. **Cam-Clay (需使用 *CLAY PLASTICITY)**
适用于正常固结或轻微超固结粘土
""",
    },

    "structural": {
        "混凝土CDP": """混凝土损伤塑性模型 (CDP) 设置：

```
*MATERIAL, NAME=CONCRETE
*ELASTIC
30000., 0.2
*CONCRETE DAMAGED PLASTICITY
30., 0.1, 1.16, 0.667, 0.
*CONCRETE COMPRESSION HARDENING
15., 0.
20., 0.0001
30., 0.001
20., 0.002
*CONCRETE TENSION STIFFENING
3.0, 0.
0.5, 0.001
*CONCRETE COMPRESSION DAMAGE
0., 0.
0.4, 0.001
0.8, 0.002
*CONCRETE TENSION DAMAGE
0., 0.
0.8, 0.001
```

关键参数：
- 膨胀角 (dilation angle): 通常 30-40°
- 偏心率: 默认 0.1
- fb0/fc0: 双轴/单轴强度比, 默认 1.16
- K: 默认 0.667
""",

        "钢筋建模": """Abaqus 钢筋建模方法：

1. **嵌入式钢筋 (*EMBEDDED ELEMENT)**
```
*EMBEDDED ELEMENT, HOST ELSET=CONCRETE
REBAR_ELEMENTS
```

2. **桁架单元 (T3D2)**
```
*ELEMENT, TYPE=T3D2, ELSET=REBAR
...
*SOLID SECTION, ELSET=REBAR, MATERIAL=STEEL
100.  (截面面积)
```

3. **Rebar Layer (用于壳单元)**
```
*REBAR LAYER
REBAR_NAME, A_rebar, spacing, position, STEEL, orient_angle
```
""",
    },

    "mechanical": {
        "接触分析": """Abaqus 接触分析设置：

1. **面-面接触 (Surface-to-Surface)**
```
*CONTACT PAIR, INTERACTION=INT-1, TYPE=SURFACE TO SURFACE
slave_surface, master_surface
*SURFACE INTERACTION, NAME=INT-1
*FRICTION
0.3
```

2. **通用接触 (General Contact, 推荐)**
```
*CONTACT
*CONTACT INCLUSIONS, ALL EXTERIOR
*CONTACT PROPERTY ASSIGNMENT
, , INT-1
```

3. **接触稳定化**
```
*CONTACT CONTROLS, STABILIZE=0.0001
```

常见问题解决：
- 穿透: 增大接触刚度或使用 ADJUST
- 不收敛: 减小增量步，启用稳定化
- 主从面选择: 粗网格为主面
""",

        "螺栓预紧力": """Abaqus 螺栓预紧力设置：

```
*STEP, NAME=Pretension
*STATIC
*PRE-TENSION SECTION, SURFACE=BOLT_CROSS_SECTION, NODE=pretension_node
BOLT_ELEMENTS
*CLOAD
pretension_node, 1, 50000.  (预紧力值)
*END STEP
```

或使用位移控制：
```
*BOUNDARY
pretension_node, 1, 1, -0.1  (预紧位移)
```
""",
    },

    "thermal": {
        "热边界条件": """Abaqus 热边界条件设置：

1. **对流**
```
*SFILM
surface_name, F, sink_temp, film_coefficient
*FILM
node_set, Fn, sink_temp, film_coefficient
```

2. **辐射**
```
*SRADIATE
surface_name, R, ambient_temp, emissivity
```

3. **热流密度**
```
*DSFLUX
surface_name, S, flux_value
```

4. **体热源**
```
*DFLUX
element_set, BF, heat_generation_rate
```
""",

        "焊接热源": """Goldak 双椭球热源模型实现：

需要使用 DFLUX 用户子程序：
```fortran
SUBROUTINE DFLUX(FLUX,SOL,KSTEP,KINC,TIME,NOEL,NPT,COORDS,JLTYP)
  ! Goldak double ellipsoid heat source
  ! Q = 6*sqrt(3)*f*P / (a*b*c*pi*sqrt(pi)) * exp(-3*x^2/a^2) * exp(-3*y^2/b^2) * exp(-3*z^2/c^2)
  ...
END SUBROUTINE
```

或使用 ABAQUS Welding Interface (AWI)
""",
    },

    "impact": {
        "Explicit设置": """Abaqus/Explicit 分析设置：

1. **基本步骤定义**
```
*STEP, NAME=Impact
*DYNAMIC, EXPLICIT
, 0.001  (分析时间)
```

2. **质量缩放**
```
*FIXED MASS SCALING, FACTOR=100, ELSET=ALL
```
或
```
*VARIABLE MASS SCALING, DT=1e-7, TYPE=BELOW MIN
```

3. **沙漏控制**
```
*SECTION CONTROLS, NAME=HOURGLASS, HOURGLASS=ENHANCED
*SOLID SECTION, ELSET=ALL, MATERIAL=MAT, CONTROLS=HOURGLASS
```

4. **输出控制**
```
*OUTPUT, FIELD, NUMBER INTERVAL=100
*OUTPUT, HISTORY, TIME INTERVAL=1e-6
```
""",

        "JohnsonCook": """Johnson-Cook 材料模型：

```
*MATERIAL, NAME=STEEL_JC
*DENSITY
7850.,
*ELASTIC
210000., 0.3
*PLASTIC, HARDENING=JOHNSON COOK
A, B, n, m, melting_temp, transition_temp
*RATE DEPENDENT, TYPE=JOHNSON COOK
C, epsilon_dot_0
*DAMAGE INITIATION, CRITERION=JOHNSON COOK
d1, d2, d3, d4, d5, melting_temp, transition_temp, ref_strain_rate
*DAMAGE EVOLUTION, TYPE=ENERGY
fracture_energy
```

典型钢材参数：
- A = 792 MPa (屈服强度)
- B = 510 MPa (硬化系数)
- n = 0.26 (硬化指数)
- C = 0.014 (应变率敏感系数)
- m = 1.03 (热软化指数)
""",
    },

    "composite": {
        "层合板建模": """复合材料层合板建模：

1. **使用壳单元**
```
*SHELL SECTION, ELSET=LAMINATE, COMPOSITE
0.125, 3, MAT_0, 0.    (厚度, 积分点数, 材料, 铺层角度)
0.125, 3, MAT_45, 45.
0.125, 3, MAT_90, 90.
0.125, 3, MAT_45, -45.
```

2. **使用 Continuum Shell (SC8R)**
```
*SOLID SECTION, ELSET=PLY1, MATERIAL=CFRP, ORIENTATION=ORI1
*ORIENTATION, NAME=ORI1, LOCAL DIRECTIONS=1
0., 0., -1., 1., 0., 0.
1, 0.
```

3. **Hashin 失效准则**
```
*DAMAGE INITIATION, CRITERION=HASHIN
Xt, Xc, Yt, Yc, Sl, St
```
""",
    },
}


def get_domain_knowledge(domain: str, query: str) -> Optional[str]:
    """
    Retrieve relevant domain knowledge for a query.

    Args:
        domain: Engineering domain
        query: User's query

    Returns:
        Relevant knowledge text or None
    """
    if domain not in DOMAIN_KNOWLEDGE:
        return None

    domain_data = DOMAIN_KNOWLEDGE[domain]

    # Simple keyword matching (will be replaced with RAG)
    query_lower = query.lower()

    for topic, content in domain_data.items():
        if topic.lower() in query_lower or any(
            keyword in query_lower
            for keyword in topic.lower().split()
        ):
            return content

    return None

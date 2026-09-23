"""
Enhanced SAT Reading Practice Test Module Prompts
Configured exactly per the 3-Phase Workflow:
- Phase 1: Content Conversion (Vision -> Markdown with visual descriptions)
- Phase 2: Question Analysis & Solving (Reasoning -> Rigorous answer key + explanations)
- Phase 3: Deliverables (questions.md & answers.md)
"""

FULL_WORKFLOW_PROMPT = """Enhanced SAT Reading Practice Test Module Prompt
You are helping me work through SAT Reading Practice Test Module 1. Follow this workflow exactly:

Phase 1: Content Conversion
- Extract all text from the test and convert it into plain, readable text format
- Identify and describe all visual elements (graphs, diagrams, charts, tables, etc.):
  - What type of visual is it?
  - What specific values/data does it contain?
  - What is the visual trying to communicate or illustrate?
  - How does it relate to the passage(s)?
- Organize the converted content logically with clear section breaks

Phase 2: Question Analysis & Solving
Work through each question sequentially (Question 1, 2, 3, etc.)
For each question:
- Restate the question clearly
- Identify the correct answer with reasoning
- Cite the relevant passage excerpt or data point that supports the answer
- Explain why other options are incorrect (if applicable)
- Zero errors — double-check your logic before finalizing each answer

Phase 3: Deliverables
Provide two separate markdown files:
- questions.md — Contains:
  - All passage text (organized by passage)
  - All visual element descriptions
  - All questions transcribed exactly
- answers.md — Contains:
  - Simple answer key formatted as: 1.A, 2.B, 3.C, ... etc.
  - Below that, detailed explanations for each answer
"""

DEFAULT_VISION_SYSTEM_PROMPT = """You are helping me work through SAT Reading & Math Practice Test Module.
Follow this workflow exactly for Phase 1 (Content Conversion):

### Phase 1: Content Conversion
1. **Extract all text** from the test screenshot and convert it into clean, readable Markdown format (transcribing all passages, stems, and options exactly as shown). If math expressions or equations are present, format them cleanly using LaTeX (`$ ... $` inline, `$$ ... $$` block).
2. **Identify and describe all visual elements** (graphs, diagrams, charts, tables, figures, etc.):
   If ANY visual element is present, include a dedicated `#### Visual Description` section with:
   - **Visual Type**: What type of visual is it? (e.g. Bar graph, Coordinate grid, Data table, Flow diagram)
   - **Specific Values / Data**: What specific values, labels, coordinates, axes, data points, or scale marks does it contain?
   - **Core Purpose**: What is the visual trying to communicate or illustrate?
   - **Relation to Passage/Question**: How does it relate to the passage or question?
3. **Organize the converted content** logically with clear section breaks:

### Question [Number]
**Passage / Stem Text:**
[Transcribed passage and question text]

#### Visual Description
*(Omit only if there are zero visuals/tables)*
- **Type**: [Visual type]
- **Data & Values**: [Exact values, axes, coordinates, percentages]
- **Illustration Purpose**: [What it communicates]
- **Relation**: [Connection to question]

**Options:**
- **A)** [Option A text]
- **B)** [Option B text]
- **C)** [Option C text]
- **D)** [Option D text]
*(Or Free-Response if open-ended)*

Do not include conversational filler. Output only clean, structured Markdown for questions.md.
"""

DEFAULT_SOLVER_SYSTEM_PROMPT = """You are helping me work through SAT Reading & Math Practice Test Module.
Follow this workflow exactly for Phase 2 (Question Analysis & Solving):

### Phase 2: Question Analysis & Solving
For the transcribed question:
1. **Restate the question clearly**:
   Summarize the core query and what is being asked.
2. **Identify the correct answer with reasoning**:
   State the exact answer clearly: `**Final Answer: [Option Letter / Value]**`
3. **Cite Evidence**:
   Cite the exact relevant passage excerpt or specific data point from the visual description that supports this answer.
4. **Explain Distractors**:
   Explain why the other options are incorrect, highlighting the specific errors or misinterpretations in those choices.
5. **Zero Errors Check**:
   Double-check your logic, evidence citation, and deduction before finalizing.

Format your response cleanly:
### Solution for Question [Number]
**Restated Question:**
[Brief restatement]

**Correct Answer & Derivation:**
[Reasoning and step-by-step proof]

**Evidence Citation:**
> [Quoted passage excerpt or specific visual data point]

**Distractor Analysis:**
- Option [X]: [Why incorrect]
- Option [Y]: [Why incorrect]

**Final Answer:**
`**Final Answer: [Option Letter]**`
"""

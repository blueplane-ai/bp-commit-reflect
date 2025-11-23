# ADR-004: Interactive Sequential Question Flow

## Status

Accepted

## Context

When capturing commit reflections, we need to gather multiple pieces of information from the developer:

1. AI synergy rating (scale 1-5)
2. Confidence level (scale 1-5)
3. Experience description (text, up to 512 chars)
4. Blockers encountered (optional text)
5. Learning moments (optional text)

We need to decide how to present these questions and collect responses. Options include:

- **All-at-once form**: Present all questions together, collect all answers at once
- **Batch prompting**: Show questions in groups, collect answers in batches
- **Sequential one-by-one**: Present one question at a time, wait for answer before next
- **Conversational flow**: AI-driven dynamic questioning based on previous answers

Additionally, we need to decide when and how to persist the data:

- **Immediate writes**: Write each answer to storage as received
- **Buffered writes**: Collect all answers in memory, write atomically at end
- **Streaming writes**: Write incrementally but support rollback

Key considerations:
- **User experience**: Should feel natural and low-friction
- **Data consistency**: Should avoid partial reflections in storage
- **Cancellation handling**: Users should be able to quit without corrupting data
- **MCP integration**: Should work well with conversational AI interfaces
- **CLI usability**: Should work smoothly in terminal environments

## Decision

We will implement an **interactive sequential question flow** where:

1. **Questions are presented one at a time** with context and progress indicators
2. **User answers one question before seeing the next**
3. **All answers are held in memory** until the final question is completed
4. **Data is written atomically** only after all required questions are answered
5. **Optional questions can be skipped** by pressing Enter or typing "skip"

### Flow Example

```
📝 Commit Reflection
─────────────────────────────────────────────────
Commit: a1b2c3d
Message: Add JWT authentication middleware
Branch: feature/auth
Files: src/auth/middleware.ts, tests/auth.test.ts
─────────────────────────────────────────────────

Question 1 of 5
❓ How well did you and AI work together on this? (1-5)
   1 = AI hindered progress, 5 = Perfect collaboration
> 4

Question 2 of 5
❓ How confident are you in these changes? (1-5)
   1 = Needs review, 5 = Production ready
> 5

Question 3 of 5
❓ How did this work feel? What was the experience like? (max 512 chars)
> Felt smooth once I got into it. The JWT library docs were clearer than expected.

Question 4 of 5 (optional)
❓ What blockers or friction did you encounter? (press Enter to skip)
> [Enter - skipped]

Question 5 of 5 (optional)
❓ What did you learn from this work? (press Enter to skip)
> Learned about HttpOnly cookies and token rotation strategies

✅ Reflection saved to .commit-reflections.jsonl
```

### State Management

**CLI Implementation:**
```python
class ReflectionSession:
    def __init__(self):
        self.session_id: str = ""
        self.commit: CommitInfo = None
        self.questions: List[Question] = []
        self.answers: Dict[str, Any] = {}
        self.current_question_index: int = 0

    # All state held in memory
    async def start(self) -> QuestionResponse:
        self.current_question_index = 0
        return self.get_current_question()

    async def submit_answer(self, answer: str, skip: bool = False) -> QuestionResponse:
        # Validate answer
        # Store in memory
        question_id = self.questions[self.current_question_index].id
        self.answers[question_id] = answer
        self.current_question_index += 1

        if self.current_question_index >= len(self.questions):
            return {
                "all_questions_answered": True,
                "ready_to_complete": True
            }

        return self.get_current_question()

    async def complete(self) -> None:
        # ONLY NOW write to storage
        await self.storage_backend.write({
            "commit": self.commit,
            "reflections": self.answers
        })
```

**MCP Server Coordination:**
```python
import subprocess
import json

class MCPServer:
    def __init__(self):
        self.sessions: Dict[str, subprocess.Popen] = {}

    async def start_commit_reflection(self, commit_info: dict) -> dict:
        # Spawn CLI process with commit context
        session_id = generate_id()
        cli_process = subprocess.Popen(
            [
                'commit-reflect',
                '--project', commit_info['project'],
                '--commit', commit_info['commit_hash'],
                '--mode', 'mcp-session',
                '--session-id', session_id
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.sessions[session_id] = cli_process

        # CLI returns first question
        return await self.read_from_cli(cli_process)

    async def answer_reflection_question(self, session_id: str, answer: str) -> dict:
        cli_process = self.sessions.get(session_id)
        # Send answer to CLI stdin
        cli_process.stdin.write(json.dumps({"answer": answer}).encode() + b'\n')
        cli_process.stdin.flush()
        # CLI validates, stores in memory, returns next question
        return await self.read_from_cli(cli_process)

    async def complete_reflection(self, session_id: str) -> dict:
        cli_process = self.sessions.get(session_id)
        # Send completion signal
        cli_process.stdin.write(json.dumps({"complete": True}).encode() + b'\n')
        cli_process.stdin.flush()
        # CLI writes to storage and exits
        return await self.read_from_cli(cli_process)
```

## Consequences

### Positive

- **Natural conversation flow**: Works well with AI chat interfaces
- **Focus**: User concentrates on one question at a time without distraction
- **Progress clarity**: Progress indicator shows position in flow
- **Data consistency**: Atomic write prevents partial reflections
- **Cancellation safety**: User can Ctrl+C without corrupting data
- **Skip flexibility**: Optional questions can be easily skipped
- **Context-aware**: Each question can show relevant commit context
- **Error recovery**: Validation errors don't lose previous answers (still in memory)

### Negative

- **Longer interaction time**: Sequential flow takes longer than a form
- **Memory requirement**: Must hold full session state in memory
- **Session timeout risk**: Long idle sessions may timeout
- **No partial save**: Can't save partial progress if user must leave
- **Backing up**: Can't go back to change previous answer without restarting

### Neutral

- **5 questions minimum**: User must answer at least 3 required questions
- **Session-based**: Requires session management in MCP server
- **Linear flow**: No branching or conditional questions (could be added later)

## Alternatives Considered

### All-at-Once Form

Present all 5 questions together in a form, collect all answers at once.

**CLI Example:**
```
Please provide the following reflections:

1. AI synergy (1-5): ____
2. Confidence (1-5): ____
3. Experience (text): ____
4. Blockers (optional): ____
5. Learning (optional): ____

Submit answers (JSON): {"ai_synergy": 4, "confidence": 5, ...}
```

**Pros:**
- Faster for experienced users
- Single validation pass
- See all questions upfront
- Can skip around

**Cons:**
- Overwhelming for first-time users
- Awkward in conversational AI interface
- Hard to provide contextual help per question
- Poor terminal UX (no good CLI form libraries)
- JSON input is error-prone

**Why rejected:** Poor fit for conversational AI workflow, overwhelming UX.

### Batch Prompting

Group questions into logical batches (e.g., ratings, then text responses).

**Example:**
```
Batch 1: Ratings
1. AI synergy (1-5):
2. Confidence (1-5):

Batch 2: Reflections
3. Experience:
4. Blockers (optional):
5. Learning (optional):
```

**Pros:**
- Fewer interaction rounds than one-by-one
- Logically grouped questions
- Still digestible

**Cons:**
- Awkward batch boundaries
- Less conversational
- Harder to provide per-question context
- More complex state management

**Why rejected:** Doesn't provide significant UX benefit over sequential flow.

### Conversational AI-Driven Flow

Let AI dynamically generate follow-up questions based on previous answers.

**Example:**
```
AI: How did this commit feel?
User: Frustrating, hit several blockers.
AI: What specific blockers did you encounter?
User: TypeScript errors and unclear documentation.
AI: What documentation was unclear?
...
```

**Pros:**
- Most natural conversational flow
- Adaptive to user responses
- Can dig deeper on interesting points
- Feels like talking to AI assistant

**Cons:**
- Non-deterministic question set
- Hard to ensure required data collected
- Difficult to analyze (variable schema)
- Can't work in non-AI contexts (direct CLI, git hooks)
- Requires LLM for every reflection

**Why rejected:** Too complex for MVP, doesn't work for non-AI contexts, variable schema.

### Immediate Write Per Question

Write each answer to storage as it's received.

**Pros:**
- No risk of losing data
- Partial reflections captured
- Simpler state management

**Cons:**
- Partial reflections pollute data
- Hard to handle cancellation (must delete partial records)
- Complex rollback logic
- Inconsistent data during session
- Multiple writes increase storage overhead

**Why rejected:** Risks data corruption, partial reflections have limited value.

### Wizard-Style Multi-Page Form (GUI)

Build a GUI application with multi-page wizard flow.

**Pros:**
- Familiar UI pattern
- Can show progress visually
- Easy to go back and edit
- Good validation UX

**Cons:**
- Requires GUI framework
- Doesn't work in terminal-only environments
- Can't integrate with AI chat workflows
- Heavy dependency
- Cross-platform GUI complexity

**Why rejected:** Must work in terminal, GUI doesn't fit CLI-first architecture.

## Implementation Notes

### Timeout Handling

Sessions automatically timeout after **30 minutes** of inactivity:

```python
from datetime import datetime, timedelta

class ReflectionSession:
    def __init__(self):
        self.last_activity: datetime = datetime.now()

    def is_timed_out(self) -> bool:
        now = datetime.now()
        elapsed = now - self.last_activity
        return elapsed > timedelta(minutes=30)
```

### Validation

Each question type has validation:

- **Scale (1-5)**: Must be integer 1-5
- **Text**: Max 512 characters for experience, unlimited for optional
- **Optional**: Empty string or "skip" allowed

Invalid answers prompt re-entry:

```
Question 3 of 5
❓ How did this work feel? (max 512 chars)
> [700 character response]

❌ Answer too long (700/512 characters). Please shorten your response.
> [revised response]
```

### Skip Handling

Optional questions accept:
- Empty input (just press Enter)
- Literal "skip" or "Skip"
- "-" or "n/a"

All treated as skipped, stored as `null` in data.

### Error Recovery

If validation fails, user re-enters answer without losing previous progress:

```python
async def submit_answer(self, answer: str) -> dict:
    question = self.questions[self.current_question_index]

    try:
        validated = self.validate(answer, question)
        self.answers[question.id] = validated
        self.current_question_index += 1
        return self.get_current_question()
    except ValidationError as e:
        # Don't advance, return same question with error
        return {
            "session_id": self.session_id,
            "error": str(e),
            "question": self.get_current_question()
        }
```

## References

- [Conversational UI Best Practices](https://uxdesign.cc/conversational-interfaces-guide-4-design-principles-8d8d1df3d478)
- [Progressive Disclosure Principle](https://www.nngroup.com/articles/progressive-disclosure/)
- ADR-001: CLI-First Architecture
- ADR-002: Model Context Protocol Integration

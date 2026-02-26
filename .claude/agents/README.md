# Agent Team: Silent Currency Bug Test Suite

This directory contains a specialized agent team designed to tackle the **Silent Currency Bug** feature challenge from multiple perspectives.

## Team Overview

### 🏗️ Data Architect (Principal)
**File**: `data-architect.md`
**Model**: Opus
**Specialty**: Data modeling, currency precision, test data architecture

**Use when you need**:
- Data schema design for multi-currency systems
- Test data generation strategies
- Currency pair test matrices
- Database constraints and validation rules

**Key strengths**:
- Prevents precision loss and rounding errors
- Designs comprehensive test data coverage
- Enforces data integrity at database level

---

### 🧪 QA Automation Expert (Senior)
**File**: `qa-automation-expert.md`
**Model**: Opus
**Mandatory Skill**: `qa-expert`

**Use when you need**:
- Overall test strategy and framework selection
- Test pyramid design (unit/integration/E2E)
- Quality gates and metrics definition
- Test case documentation (Google Testing Standards)

**Key strengths**:
- 15+ years QA automation experience
- Comprehensive test coverage planning
- CI/CD integration expertise
- Quality assurance best practices

---

### 🧪 QA Engineer 1 (Senior, Backend Focus)
**File**: `qa-engineer-backend-1.md`
**Model**: Sonnet
**Specialty**: API integration tests, currency conversion testing

**Use when you need**:
- Integration test implementation (API-level)
- Currency conversion logic testing
- Checkout and authorization flow tests
- Test utilities and fixtures

**Key strengths**:
- QA mindset with backend technical skills
- RESTful API testing expertise
- FX rate mocking and stubbing strategies
- Parameterized test patterns

---

### 🧪 QA Engineer 2 (Senior, Backend Focus)
**File**: `qa-engineer-backend-2.md`
**Model**: Sonnet
**Specialty**: Webhook testing, settlement verification, async testing

**Use when you need**:
- Webhook payload validation tests
- Settlement amount verification
- End-to-end transaction flow testing
- Asynchronous operation testing

**Key strengths**:
- Event-driven system testing
- Financial reconciliation validation
- Webhook testing patterns
- Async and concurrency testing

---

### 🔴 Devil's Advocate (Principal)
**File**: `devils-advocate.md`
**Model**: Opus
**Specialty**: Edge case identification, security challenges, critical thinking

**Use when you need**:
- Test coverage critique
- Security and fraud scenario identification
- Assumption challenging
- Production readiness validation

**Key strengths**:
- Finds overlooked edge cases
- Adversarial security thinking
- Production failure pattern recognition
- Constructive criticism

---

## How to Use This Team

### Quick Start

To invoke a specific agent in your Claude Code session:

```bash
# Launch the data architect
@data-architect

# Launch the QA automation expert (with mandatory qa-expert skill)
@qa-automation-expert

# Launch QA engineer 1 (backend focus)
@qa-engineer-backend-1

# Launch QA engineer 2 (backend focus)
@qa-engineer-backend-2

# Launch devil's advocate
@devils-advocate
```

### Recommended Workflow

Follow the phases outlined in `TEAM_CHARTER.md`:

#### Phase 1: Discovery & Planning (20 min)
```
1. @data-architect - Analyze incident and design data model
2. @qa-automation-expert - Develop test strategy
3. @devils-advocate - Review and identify initial edge cases
```

#### Phase 2: Design & Architecture (20 min)
```
1. @data-architect - Present currency pair matrix
2. @qa-automation-expert - Present test pyramid strategy
3. @qa-engineer-backend-1 - Propose API test approach
4. @qa-engineer-backend-2 - Propose webhook test approach
5. @devils-advocate - Challenge assumptions
```

#### Phase 3: Implementation (60 min)
```
1. @qa-engineer-backend-1 - Build integration tests
2. @qa-engineer-backend-2 - Build webhook tests
3. @data-architect - Create data factories
4. @qa-automation-expert - Track progress & CI config
5. @devils-advocate - Continuous review
```

#### Phase 4: Integration & Documentation (30 min)
```
1. All QA engineers - Integrate test suite
2. @data-architect - Finalize data documentation
3. @qa-automation-expert - Complete Test Strategy doc
4. @devils-advocate - Edge case catalog
```

#### Phase 5: Review & Polish (10 min)
```
1. @devils-advocate - Final production readiness review
2. @qa-automation-expert - Validate against criteria
```

### Parallel Execution

You can launch multiple agents simultaneously for faster collaboration:

```bash
# Launch data architect and QA expert together for planning
@data-architect @qa-automation-expert

# Launch both QA engineers for parallel test implementation
@qa-engineer-backend-1 @qa-engineer-backend-2
```

### Team Coordination

The **QA Automation Expert** acts as team coordinator:
- Tracks overall progress
- Ensures deliverables meet evaluation criteria
- Facilitates decision-making
- Maintains quality standards

The **Devil's Advocate** acts as critical reviewer:
- Continuously challenges assumptions
- Identifies blind spots
- Ensures production readiness
- Escalates security concerns

---

## Team Responsibilities Matrix

| Agent | Data Models | Test Strategy | Integration Tests | Webhooks | Edge Cases | Documentation |
|-------|-------------|---------------|-------------------|----------|------------|---------------|
| Data Architect | ✅ Lead | Support | Support | Support | Identify | ✅ Data docs |
| QA Automation Expert | Review | ✅ Lead | Review | Review | Prioritize | ✅ Test strategy |
| QA Engineer 1 | Implement | Support | ✅ Lead | Support | Implement | Tech docs |
| QA Engineer 2 | Implement | Support | Support | ✅ Lead | Implement | Tech docs |
| Devil's Advocate | Challenge | Challenge | Review | Review | ✅ Lead | ✅ Critique |

---

## Expected Deliverables

### From Data Architect
- [ ] Data model documentation (schemas, constraints)
- [ ] Test data strategy document
- [ ] Currency pair test matrix
- [ ] Data factory specifications

### From QA Automation Expert
- [ ] Test Strategy & Design Decisions document (CRITICAL)
- [ ] Test case documentation (Google Testing Standards)
- [ ] CI/CD workflow configuration
- [ ] Quality metrics and coverage analysis

### From QA Engineer 1
- [ ] Integration test suite (checkout/authorization)
- [ ] Currency conversion test implementation
- [ ] Test utilities and fixtures
- [ ] API mocking strategy documentation

### From QA Engineer 2
- [ ] Webhook test suite
- [ ] Settlement verification tests
- [ ] End-to-end data flow tests
- [ ] Async testing utilities

### From Devil's Advocate
- [ ] Edge case catalog (with severity assessment)
- [ ] Security threat model
- [ ] Test strategy critique
- [ ] Production readiness review

---

## Success Criteria

The team targets **top quartile** performance on:

1. **Authorization Amount Correctness** (20-25 pts): Tests catch the original rounding bug and verify amounts across 5+ currency pairs
2. **Edge Case Identification** (15-20 pts): 4+ well-chosen edge cases with payment-specific insights
3. **Test Architecture** (15-20 pts): Excellent reusable patterns, easy to extend for new currencies
4. **Test Strategy Document** (10-15 pts): Exceptional strategic thinking with clear trade-offs
5. **CI/CD Integration** (5-7 pts): Production-ready workflow with parallel execution
6. **Code Quality** (8-10 pts): Exemplary test clarity and best practices

**Target Total**: 85-93 out of 93 points

---

## Tips for Effective Team Usage

1. **Start with Planning**: Don't jump into implementation. Let the Data Architect and QA Expert design first.

2. **Use Devil's Advocate Early**: Don't wait until the end. Challenge assumptions throughout.

3. **Divide Responsibilities Clearly**: QA Engineer 1 handles checkout/auth API tests, QA Engineer 2 handles webhooks/settlement.

4. **Document Decisions**: Every agent should explain their reasoning—this feeds into the Test Strategy doc.

5. **Think Production-Ready**: The Devil's Advocate should constantly ask "Would this prevent the incident in production?"

6. **Prioritize Based on Scoring**: Focus on what gets the most points:
   - Authorization amount correctness (25 pts)
   - Edge cases (20 pts)
   - Architecture (20 pts)
   - Strategy doc (15 pts)

---

## File Structure

```
.claude/agents/
├── README.md                      # This file
├── TEAM_CHARTER.md                # Detailed team workflow and protocols
├── data-architect.md              # Principal Data Architect agent
├── qa-automation-expert.md        # Senior QA Expert agent (with qa-expert skill)
├── qa-engineer-backend-1.md       # Senior QA Engineer (API/integration testing)
├── qa-engineer-backend-2.md       # Senior QA Engineer (webhooks/settlement testing)
└── devils-advocate.md             # Principal Engineer (critical reviewer)
```

---

## Questions?

- **Which agent should I start with?** Start with `@data-architect` and `@qa-automation-expert` for planning.
- **Can I use just one agent?** Yes, but you'll miss the multi-perspective approach designed for this challenge.
- **How do agents collaborate?** You coordinate by sharing outputs between agents. The `TEAM_CHARTER.md` defines the workflow.
- **What if agents disagree?** The QA Automation Expert facilitates; Devil's Advocate has veto on security concerns.

---

**Remember**: This team is designed to prevent a €2.3M incident. Use them strategically, let each agent play to their strengths, and build a test suite that would truly catch this bug in production.

# Agent Team Charter: Silent Currency Bug Test Suite

## Mission
Build a comprehensive automated test suite that would have prevented the €2.3M multi-currency incident and ensure it never happens again.

## Team Composition

### 1. Data Architect (Principal)
- **Agent**: `data-architect`
- **Model**: Opus
- **Primary Focus**: Data modeling, test data strategy, currency pair matrices, validation constraints
- **Key Deliverables**:
  - Data model documentation (schemas, constraints, validation rules)
  - Test data strategy document
  - Currency pair test matrix
  - Data factory specifications

### 2. QA Automation Expert (Senior)
- **Agent**: `qa-automation-expert` (with mandatory `qa-expert` skill)
- **Model**: Opus
- **Primary Focus**: Test strategy, framework selection, test pyramid design, quality gates
- **Key Deliverables**:
  - Overall test strategy document
  - Test case documentation (Google Testing Standards)
  - Quality metrics and coverage analysis
  - CI/CD test execution plan

### 3. QA Engineer 1 (Senior, Backend Focus)
- **Agent**: `qa-engineer-backend-1`
- **Model**: Sonnet
- **Primary Focus**: API integration tests, currency conversion testing, checkout/authorization flow
- **Key Deliverables**:
  - Integration test suite (API-level)
  - Currency conversion test implementation
  - Test utilities and fixtures
  - API mocking strategy documentation

### 4. QA Engineer 2 (Senior, Backend Focus)
- **Agent**: `qa-engineer-backend-2`
- **Model**: Sonnet
- **Primary Focus**: Webhook testing, settlement verification, async data flow validation
- **Key Deliverables**:
  - Webhook test suite
  - Settlement verification tests
  - End-to-end data flow tests
  - Async testing utilities

### 5. Devil's Advocate (Principal)
- **Agent**: `devils-advocate`
- **Model**: Opus
- **Primary Focus**: Edge case identification, security challenges, test coverage critique
- **Key Deliverables**:
  - Edge case catalog
  - Security threat model
  - Test strategy critique
  - Production readiness review

## Collaboration Workflow

### Phase 1: Discovery & Planning (20 minutes)
1. **Data Architect** analyzes the incident root cause and designs data model + test data strategy
2. **QA Automation Expert** develops overall test strategy and prioritizes coverage
3. **Devil's Advocate** reviews incident details and identifies initial overlooked edge cases
4. **Backend Engineers** review technical context and assess testing approach

### Phase 2: Design & Architecture (20 minutes)
1. **Data Architect** presents currency pair test matrix and data factory design
2. **QA Automation Expert** presents test pyramid strategy and framework recommendations
3. **QA Engineer 1** proposes API integration test approach
4. **QA Engineer 2** proposes webhook/settlement test approach
5. **Devil's Advocate** challenges assumptions and surfaces edge cases

### Phase 3: Implementation (60 minutes)
1. **QA Engineer 1** builds integration tests for checkout/authorization flow (Core Req 1)
2. **QA Engineer 2** builds webhook and settlement tests (Core Req 1)
3. **Both QA Engineers** implement edge case tests (Core Req 2)
4. **Data Architect** creates data factories and test fixtures (Core Req 3)
5. **QA Automation Expert** tracks progress, ensures test quality, prepares CI config
6. **Devil's Advocate** continuously reviews code and identifies gaps

### Phase 4: Integration & Documentation (30 minutes)
1. **QA Engineers** integrate all tests into cohesive suite
2. **Data Architect** finalizes test data documentation
3. **QA Automation Expert** completes Test Strategy & Design Decisions document
4. **Devil's Advocate** produces edge case catalog and security threat model
5. **Team** collaborates on README and setup instructions

### Phase 5: Review & Polish (10 minutes)
1. **Devil's Advocate** performs final production readiness review
2. **QA Automation Expert** validates against evaluation criteria
3. **Team** ensures all deliverables are complete

## Communication Protocols

### Decision-Making
- **Data Architecture Decisions**: Data Architect has final say (with Devil's Advocate review)
- **Test Strategy Decisions**: QA Automation Expert has final say
- **Implementation Details**: QA Engineers collaborate and decide
- **Edge Case Prioritization**: Team vote with Devil's Advocate input

### Conflict Resolution
- If disagreement on approach: QA Automation Expert facilitates discussion
- If security concern raised: Devil's Advocate has veto power
- If time constraint forces trade-off: Team prioritizes based on evaluation criteria scoring

### Progress Tracking
- QA Automation Expert maintains checklist of Core Requirements 1-3
- Each agent reports blockers immediately
- Devil's Advocate tracks outstanding edge cases

## Success Criteria

The team succeeds when the deliverables achieve:
- ✅ Top quartile on "Authorization Amount Correctness & Bug Detection" (20-25 pts)
- ✅ Top quartile on "Edge Case Identification & Handling" (15-20 pts)
- ✅ Top quartile on "Test Architecture & Maintainability" (15-20 pts)
- ✅ Top quartile on "Test Strategy & Design Decisions Document" (10-15 pts)
- ✅ Median or better on all other criteria

**Target Score**: 85-93 out of 93 points (Top Quartile Overall)

## Team Roles Summary

| Agent | Focus | Time Allocation |
|-------|-------|-----------------|
| Data Architect | Data models, test data, currency matrices | 30% strategy, 40% data factories, 30% documentation |
| QA Automation Expert | Test strategy, quality gates, coordination | 40% strategy doc, 30% test oversight, 30% CI/reporting |
| QA Engineer 1 | Integration tests, API testing, currency conversion | 70% test implementation, 30% utilities |
| QA Engineer 2 | Webhook tests, settlement, async flows | 70% test implementation, 30% async utilities |
| Devil's Advocate | Edge cases, security, critique | 50% review/challenge, 50% threat modeling |

## Key Deliverables Checklist

- [ ] Automated test suite (Core Req 1 & 2)
- [ ] Test framework setup with reusable patterns (Core Req 3)
- [ ] CI/CD workflow configuration
- [ ] README with setup instructions
- [ ] Test Strategy & Design Decisions document
- [ ] Data model documentation (Data Architect)
- [ ] Edge case catalog (Devil's Advocate)
- [ ] Security threat model (Devil's Advocate)

---

**Remember**: The goal is not just passing tests—it's preventing a €2.3M incident from ever happening again. Think like the payment platform depends on your work, because in production, it would.

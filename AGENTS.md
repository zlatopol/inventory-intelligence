## Project

This repository contains a portfolio project called **Inventory Intelligence Platform**.

The project is based on the educational assignment about an information system for the supply department of a wholesale warehouse.

The original educational requirements are the foundation of the project, but the final implementation should be significantly expanded into a realistic portfolio project relevant to an **ML Engineer** role.

---

## Developer Profile

The developer has:

* basic Python knowledge;
* basic SQL knowledge;
* practical experience with PostgreSQL;
* basic Git experience;
* basic Docker experience;
* some experience working with APIs;
* no significant commercial software engineering experience yet.

The project is also a learning project.

The goal is not only to produce working software, but to develop the developer's ability to design, implement, test, debug and explain a real system.

---

# Primary Objective

Build a complete, production-oriented inventory management and intelligence system.

The system should eventually support:

* products;
* stores;
* warehouses;
* inventory;
* stock movements;
* purchase/supply operations;
* store requests;
* historical data;
* demand forecasting;
* inventory analysis;
* stockout risk;
* order recommendations;
* anomaly detection.

The system should demonstrate real engineering practices rather than technology collecting.

---

# Engineering Philosophy

Follow this priority:

1. Correctness
2. Understanding
3. Simplicity
4. Maintainability
5. Testability
6. Performance
7. Scalability

Do not introduce complexity without a concrete reason.

Avoid premature:

* microservices;
* Kubernetes;
* Kafka;
* distributed systems;
* complex orchestration;
* unnecessary abstractions.

Start with a **modular monolith**.

---

# Preferred Technology Stack

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic

## Database

* PostgreSQL

## Testing

* pytest
* integration tests
* API tests

## Data

* pandas or Polars
* NumPy
* SQL

## Machine Learning

* scikit-learn
* XGBoost/LightGBM when justified
* MLflow

## Infrastructure

* Docker
* Docker Compose
* GitHub Actions

Use additional technologies only when there is a clear engineering justification.

---

# Architecture Principles

Prefer:

```text
API
 ↓
Application/Service layer
 ↓
Repository/Data Access layer
 ↓
PostgreSQL
```

Business logic should not be placed directly inside API handlers.

Keep domain boundaries clear.

Avoid both:

* massive files/functions;
* excessive abstraction.

Use abstractions when they solve an actual problem.

---

# Database Principles

PostgreSQL is the source of truth for application data.

Pay attention to:

* primary keys;
* foreign keys;
* constraints;
* normalization;
* relationships;
* indexes;
* transactions;
* data integrity;
* query performance.

When performance matters, investigate with:

```text
EXPLAIN
EXPLAIN ANALYZE
```

Do not claim that an index or optimization helps without measuring when measurement is practical.

All schema changes must use Alembic migrations.

---

# Data Principles

Historical data is important because the project contains an ML component.

The system should preserve meaningful historical events such as:

* stock receipts;
* sales/stock consumption;
* stock movements;
* store requests;
* purchase orders;
* deliveries;
* inventory changes.

Whenever possible, preserve timestamps and enough information to reconstruct historical states.

---

# Machine Learning Principles

The primary ML task is:

**Demand Forecasting**

Potential prediction target:

```text
demand(store, product, future_period)
```

Always start with a baseline before using complex models.

Possible baselines:

* previous value;
* moving average;
* seasonal naive baseline.

For time-series forecasting, do not use random train/test splitting without explicitly justifying it.

Pay particular attention to:

* temporal leakage;
* target leakage;
* feature leakage;
* overfitting;
* chronological validation;
* walk-forward validation.

Every ML feature should have a reason for existing.

Every metric should have a justification.

---

# Learning Mode

This project is educational.

When a task has significant learning value, do not immediately provide the complete solution.

Prefer:

```text
Problem
 ↓
Explanation
 ↓
Developer proposes solution
 ↓
Review
 ↓
Improvement
 ↓
Implementation
 ↓
Tests
```

The developer should understand the important decisions behind the implementation.

For routine or mechanical tasks, the agent may work autonomously.

---

# Autonomous Mode

The agent may independently:

* inspect the repository;
* modify files;
* create files;
* run tests;
* run linters;
* debug errors;
* update documentation;
* implement routine functionality.

Before a significant change:

1. inspect the existing code;
2. explain the plan;
3. identify affected files;
4. implement the change;
5. run relevant checks;
6. report the result.

Do not modify unrelated code.

---

# Testing

Do not consider a feature complete merely because the application starts.

Use appropriate tests:

### Unit tests

For:

* business logic;
* calculations;
* feature engineering.

### Integration tests

For:

* PostgreSQL;
* repositories;
* transactions.

### API tests

For:

* endpoints;
* validation;
* error handling.

### ML tests

For:

* feature generation;
* prediction output;
* model loading;
* leakage-sensitive logic where appropriate.

Prefer meaningful tests over artificial coverage targets.

---

# Debugging

When something fails:

```text
Symptom
 ↓
Reproduce
 ↓
Collect evidence
 ↓
Hypothesis
 ↓
Test hypothesis
 ↓
Fix
 ↓
Regression test
```

Do not guess the cause of an error when it can be verified.

Never hide uncertainty.

If an earlier recommendation was wrong, explicitly acknowledge it and correct it.

---

# Git

Use small, logical commits.

Preferred style:

```text
feat: add product domain model
feat: add inventory repository
feat: implement stock movement service
test: add inventory integration tests
fix: prevent negative inventory
```

Before committing, inspect:

```text
git status
git diff
```

Never perform destructive Git operations without explicit permission.

Do not use:

* git reset --hard;
* force push;
* destructive branch operations;

unless explicitly authorized.

---

# Documentation

Keep important project knowledge inside the repository.

Important documentation will live in:

```text
docs/
```

Expected documents include:

```text
docs/
├── requirements.md
├── project-status.md
├── architecture.md
├── database.md
├── ml.md
└── decisions/
```

Documentation should explain decisions, not merely describe code.

---

# Requirements

The original educational assignment requirements must be preserved.

Do not invent requirements.

When a requirement is derived from the educational material, keep its original meaning.

Separate:

1. original assignment requirements;
2. project extensions;
3. optional future features.

---

# Communication

For significant tasks, use this structure:

## Goal

What are we trying to achieve?

## Why

Why is it needed?

## Plan

What are the steps?

## Implementation

What was changed?

## Validation

What was tested?

## Engineering Decision

What important decision was made and why?

## Learning

What should the developer understand?

## Next Step

What should happen next?

Keep explanations proportional to the task.

---

# Definition of Done

A feature is considered complete when:

* implementation works;
* relevant tests exist;
* relevant checks pass;
* migrations are valid when applicable;
* documentation is updated when necessary;
* no unrelated code was changed;
* important architectural decisions are understood by the developer.

---

# Core Principle

Do not optimize for:

> "Generate as much code as possible."

Optimize for:

> "Build a realistic system while making the developer capable of explaining and maintaining it independently."

The final project should demonstrate the ability to go from:

```text
Requirements
 ↓
Architecture
 ↓
Database
 ↓
Backend
 ↓
Data
 ↓
ML
 ↓
Testing
 ↓
Deployment
 ↓
Monitoring
```

and understand why each part exists.

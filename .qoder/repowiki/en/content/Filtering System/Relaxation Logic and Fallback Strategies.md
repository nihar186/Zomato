# Relaxation Logic and Fallback Strategies

<cite>
**Referenced Files in This Document**
- [pipeline.py](file://src/filtering/pipeline.py)
- [filters.py](file://src/filtering/filters.py)
- [result.py](file://src/filtering/result.py)
- [config.py](file://src/config.py)
- [preferences.py](file://src/domain/preferences.py)
- [preferences_validator.py](file://src/filtering/preferences_validator.py)
- [test_pipeline.py](file://tests/test_pipeline.py)
- [test_filters.py](file://tests/test_filters.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document explains the relaxation mechanism that ensures minimum candidate generation in the filtering pipeline. It details the four-step relaxation process: budget widening, keyword filter removal, minimum rating reduction, and cuisine filter dropping. The document covers trigger criteria, execution order, improvement detection logic, configurable parameters, scenario examples, performance impact analysis, and transparency mechanisms for tracking which filters were relaxed.

## Project Structure
The relaxation logic resides primarily in the filtering module, with supporting components in configuration, domain models, and tests.

```mermaid
graph TB
subgraph "Filtering Module"
FS["FilterService<br/>(pipeline.py)"]
FL["Filters<br/>(filters.py)"]
FR["FilterResult<br/>(result.py)"]
end
subgraph "Domain Models"
UP["UserPreferences<br/>(preferences.py)"]
RS["Restaurant<br/>(domain/restaurant.py)"]
end
subgraph "Configuration"
CFG["Settings<br/>(config.py)"]
PV["PreferenceValidator<br/>(preferences_validator.py)"]
end
subgraph "Tests"
TPL["test_pipeline.py"]
TFL["test_filters.py"]
end
FS --> FL
FS --> FR
FS --> CFG
FS --> PV
FS --> UP
FS --> RS
TPL --> FS
TFL --> FL
```

**Diagram sources**
- [pipeline.py:31-103](file://src/filtering/pipeline.py#L31-L103)
- [filters.py:118-125](file://src/filtering/filters.py#L118-L125)
- [result.py:11-20](file://src/filtering/result.py#L11-L20)
- [config.py:46-71](file://src/config.py#L46-L71)
- [preferences.py:15-29](file://src/domain/preferences.py#L15-L29)
- [preferences_validator.py:28-76](file://src/filtering/preferences_validator.py#L28-L76)
- [test_pipeline.py:76-117](file://tests/test_pipeline.py#L76-L117)
- [test_filters.py:92-95](file://tests/test_filters.py#L92-L95)

**Section sources**
- [pipeline.py:1-204](file://src/filtering/pipeline.py#L1-L204)
- [filters.py:1-125](file://src/filtering/filters.py#L1-L125)
- [result.py:1-20](file://src/filtering/result.py#L1-L20)
- [config.py:1-81](file://src/config.py#L1-L81)
- [preferences.py:1-29](file://src/domain/preferences.py#L1-L29)
- [preferences_validator.py:1-76](file://src/filtering/preferences_validator.py#L1-L76)
- [test_pipeline.py:1-131](file://tests/test_pipeline.py#L1-L131)
- [test_filters.py:1-125](file://tests/test_filters.py#L1-L125)

## Core Components
- FilterService: Orchestrates the deterministic pipeline and applies relaxation when candidate count falls below the configured minimum.
- Filters: Individual filter functions for city, rating, cuisine, budget, keyword filtering, sorting, and truncation.
- FilterResult: Encapsulates the final results, including whether filters were relaxed and the sequence of relaxation steps taken.
- Settings: Configurable parameters controlling minimum and maximum candidates, among other system settings.
- UserPreferences: Domain model for user-specified preferences including budget, cuisine, minimum rating, and additional preferences.
- PreferenceValidator: Resolves user location to a canonical city and provides suggestions when needed.

Key relaxation constants:
- Rating floor and step values are defined within the pipeline module for controlled rating reduction.

**Section sources**
- [pipeline.py:31-103](file://src/filtering/pipeline.py#L31-L103)
- [filters.py:118-125](file://src/filtering/filters.py#L118-L125)
- [result.py:11-20](file://src/filtering/result.py#L11-L20)
- [config.py:46-71](file://src/config.py#L46-L71)
- [preferences.py:15-29](file://src/domain/preferences.py#L15-L29)
- [preferences_validator.py:28-76](file://src/filtering/preferences_validator.py#L28-L76)

## Architecture Overview
The relaxation mechanism operates after the initial deterministic pipeline. If the resulting candidate set is smaller than the configured minimum, the system iteratively relaxes filters until either sufficient candidates are found or all relaxation steps have been exhausted.

```mermaid
sequenceDiagram
participant Client as "Caller"
participant Service as "FilterService"
participant Pipeline as "_run_pipeline"
participant Relax as "_relax"
participant Filters as "Filters"
participant Result as "FilterResult"
Client->>Service : "apply(preferences, restaurants)"
Service->>Pipeline : "initial pipeline (strict filters)"
Pipeline->>Filters : "filter_by_rating"
Filters-->>Pipeline : "rated candidates"
Pipeline->>Filters : "filter_by_cuisine"
Filters-->>Pipeline : "cuisine-filtered candidates"
Pipeline->>Filters : "filter_by_budget (relaxed=False)"
Filters-->>Pipeline : "budget-filtered candidates"
Pipeline->>Filters : "apply_keyword_filter (optional)"
Filters-->>Pipeline : "keyword-filtered candidates"
Pipeline->>Filters : "sort_candidates"
Filters-->>Pipeline : "sorted candidates"
Pipeline-->>Service : "initial candidates, [] steps"
alt "candidates < min_candidates"
Service->>Relax : "_relax(base, preferences, candidates, steps)"
Relax->>Pipeline : "step 1 : widen budget"
Pipeline->>Filters : "filter_by_budget (relaxed=True)"
Filters-->>Pipeline : "widened candidates"
Pipeline-->>Relax : "widened candidates"
alt "improvement detected"
Relax->>Relax : "append 'budget_widened'"
end
alt "still insufficient"
Relax->>Pipeline : "step 2 : drop keyword filter"
Pipeline-->>Relax : "without keyword candidates"
alt "improvement detected"
Relax->>Relax : "append 'keyword_dropped'"
end
end
alt "still insufficient"
Relax->>Relax : "step 3 : lower min_rating (loop)"
loop "while candidates < min_candidates and rating > floor"
Relax->>Pipeline : "re-run with lowered min_rating"
Pipeline-->>Relax : "lowered candidates"
alt "improvement detected"
Relax->>Relax : "append 'min_rating_lowered_to_X'"
end
end
end
alt "still insufficient"
Relax->>Pipeline : "step 4 : drop cuisine filter"
Pipeline-->>Relax : "without cuisine candidates"
alt "improvement detected"
Relax->>Relax : "append 'cuisine_dropped'"
end
end
end
Service->>Filters : "truncate to max_candidates"
Filters-->>Service : "final candidates"
Service-->>Result : "return FilterResult"
```

**Diagram sources**
- [pipeline.py:42-103](file://src/filtering/pipeline.py#L42-L103)
- [pipeline.py:105-129](file://src/filtering/pipeline.py#L105-L129)
- [pipeline.py:131-203](file://src/filtering/pipeline.py#L131-L203)
- [filters.py:37-125](file://src/filtering/filters.py#L37-L125)
- [result.py:11-20](file://src/filtering/result.py#L11-L20)

## Detailed Component Analysis

### Relaxation Trigger Criteria
- Trigger condition: After the initial pipeline, if the number of candidates is less than the configured minimum threshold.
- Minimum threshold: Controlled by Settings.min_candidates.
- Improvement detection: A relaxation step is considered successful if it increases the candidate count compared to the previous iteration or yields a non-empty set when the current set is empty.

```mermaid
flowchart TD
Start(["After initial pipeline"]) --> CheckMin["len(candidates) < min_candidates?"]
CheckMin --> |No| Truncate["Truncate to max_candidates"] --> End(["Return FilterResult"])
CheckMin --> |Yes| Step1["Widen budget band"] --> Improved1{"Improved?"}
Improved1 --> |Yes| Append1["Append 'budget_widened'"] --> Next1["candidates = widened"]
Improved1 --> |No| Next1
Next1 --> CheckMin2["len(candidates) < min_candidates?"]
CheckMin2 --> |No| Truncate --> End
CheckMin2 --> |Yes| Step2["Drop keyword filter"] --> Improved2{"Improved?"}
Improved2 --> |Yes| Append2["Append 'keyword_dropped'"] --> Next2["candidates = without_keyword"]
Improved2 --> |No| Next2
Next2 --> CheckMin3["len(candidates) < min_candidates?"]
CheckMin3 --> |No| Truncate --> End
CheckMin3 --> |Yes| Step3["Lower min_rating (loop)"] --> Improved3{"Improved?"}
Improved3 --> |Yes| Append3["Append 'min_rating_lowered_to_X'"] --> Next3["candidates = lowered"]
Improved3 --> |No| Next3
Next3 --> CheckMin4["len(candidates) < min_candidates?"]
CheckMin4 --> |No| Truncate --> End
CheckMin4 --> |Yes| Step4["Drop cuisine filter"] --> Improved4{"Improved?"}
Improved4 --> |Yes| Append4["Append 'cuisine_dropped'"] --> Next4["candidates = without_cuisine"]
Improved4 --> |No| Next4
Next4 --> Truncate --> End
```

**Diagram sources**
- [pipeline.py:75-82](file://src/filtering/pipeline.py#L75-L82)
- [pipeline.py:145-201](file://src/filtering/pipeline.py#L145-L201)

**Section sources**
- [pipeline.py:75-82](file://src/filtering/pipeline.py#L75-L82)
- [pipeline.py:145-201](file://src/filtering/pipeline.py#L145-L201)
- [config.py:56](file://src/config.py#L56)

### Four-Step Relaxation Process

#### Step 1: Budget Widening
- Purpose: Expand the allowed budget bands to increase candidate availability.
- Mechanism: Uses expanded budget bands when relaxed=True.
- Detection: Appended to relaxation_steps as "budget_widened" if improvement is observed.

```mermaid
flowchart TD
A["Initial candidates"] --> B["Run pipeline with budget_relaxed=True"]
B --> C{"len(new) > len(old) or new > 0 and old == 0?"}
C --> |Yes| D["Append 'budget_widened'"]
C --> |No| E["Keep old candidates"]
D --> F["candidates = widened"]
E --> F
```

**Diagram sources**
- [pipeline.py:146-157](file://src/filtering/pipeline.py#L146-L157)
- [filters.py:18-24](file://src/filtering/filters.py#L18-L24)
- [filters.py:59-66](file://src/filtering/filters.py#L59-L66)

**Section sources**
- [pipeline.py:146-157](file://src/filtering/pipeline.py#L146-L157)
- [filters.py:18-24](file://src/filtering/filters.py#L18-L24)
- [filters.py:59-66](file://src/filtering/filters.py#L59-L66)

#### Step 2: Keyword Filter Removal
- Purpose: Remove the soft keyword filter to broaden results.
- Mechanism: Re-runs pipeline with apply_keyword=False.
- Detection: Appended to relaxation_steps as "keyword_dropped" if improvement is observed.

```mermaid
flowchart TD
A["Current candidates"] --> B["Run pipeline with apply_keyword=False"]
B --> C{"len(new) > len(old)?"}
C --> |Yes| D["Append 'keyword_dropped'"]
C --> |No| E["Keep old candidates"]
D --> F["candidates = without_keyword"]
E --> F
```

**Diagram sources**
- [pipeline.py:160-170](file://src/filtering/pipeline.py#L160-L170)
- [filters.py:84-101](file://src/filtering/filters.py#L84-L101)

**Section sources**
- [pipeline.py:160-170](file://src/filtering/pipeline.py#L160-L170)
- [filters.py:84-101](file://src/filtering/filters.py#L84-L101)

#### Step 3: Minimum Rating Reduction
- Purpose: Lower the minimum rating threshold to include more candidates.
- Mechanism: Iteratively reduces min_rating by a fixed step until improvement is observed or the rating floor is reached.
- Detection: Appended to relaxation_steps with the specific rating value (e.g., "min_rating_lowered_to_4.0").

```mermaid
flowchart TD
Start(["current min_rating"]) --> Loop{"len(candidates) < min_candidates and min_rating > floor?"}
Loop --> |No| End(["Stop lowering"])
Loop --> |Yes| Lower["min_rating = max(floor, min_rating - step)"]
Lower --> Run["Re-run pipeline with new min_rating"]
Run --> Improved{"len(new) > len(old)?"}
Improved --> |Yes| Append["Append 'min_rating_lowered_to_X'"]
Improved --> |No| Keep["Keep old candidates"]
Append --> Loop
Keep --> Loop
```

**Diagram sources**
- [pipeline.py:172-187](file://src/filtering/pipeline.py#L172-L187)
- [pipeline.py:27-28](file://src/filtering/pipeline.py#L27-L28)

**Section sources**
- [pipeline.py:172-187](file://src/filtering/pipeline.py#L172-L187)
- [pipeline.py:27-28](file://src/filtering/pipeline.py#L27-L28)

#### Step 4: Cuisine Filter Dropping
- Purpose: Remove the cuisine filter to maximize candidate availability.
- Mechanism: Re-runs pipeline with cuisine="".
- Detection: Appended to relaxation_steps as "cuisine_dropped" if improvement is observed.

```mermaid
flowchart TD
A["Current candidates"] --> B["Run pipeline with cuisine=''"]
B --> C{"len(new) > len(old)?"}
C --> |Yes| D["Append 'cuisine_dropped'"]
C --> |No| E["Keep old candidates"]
D --> F["candidates = without_cuisine"]
E --> F
```

**Diagram sources**
- [pipeline.py:189-201](file://src/filtering/pipeline.py#L189-L201)
- [filters.py:47-56](file://src/filtering/filters.py#L47-L56)

**Section sources**
- [pipeline.py:189-201](file://src/filtering/pipeline.py#L189-L201)
- [filters.py:47-56](file://src/filtering/filters.py#L47-L56)

### Improvement Detection Logic
- Comparison metric: len(new_candidates) > len(current_candidates).
- Special case: If the new set is non-empty while the current set is empty, the step is still considered an improvement and recorded.
- This ensures that even if the absolute count does not increase, any step that yields at least one candidate is treated as beneficial.

**Section sources**
- [pipeline.py:142-143](file://src/filtering/pipeline.py#L142-L143)
- [pipeline.py:153-155](file://src/filtering/pipeline.py#L153-L155)

### Configurable Parameters
- min_candidates: Minimum number of candidates required before relaxation is triggered.
- max_candidates: Maximum number of candidates to return after truncation.
- top_n_results: Number of top results to return (used in recommendation pipeline).
- Rating floor and step: Controls the lower bound and decrement granularity for min_rating relaxation.
- Additional LLM-related settings: Not directly part of relaxation but influence overall system behavior.

**Section sources**
- [config.py:55-57](file://src/config.py#L55-L57)
- [config.py:66-71](file://src/config.py#L66-L71)
- [pipeline.py:27-28](file://src/filtering/pipeline.py#L27-L28)

### Transparency and Tracking
- filters_relaxed: Boolean flag indicating whether any relaxation was applied.
- relaxation_steps: Ordered list of steps taken, enabling full auditability of the decision-making process.
- empty_reason: Set to "no_matches_after_relaxation" when no candidates remain even after relaxation.

**Section sources**
- [result.py:15-16](file://src/filtering/result.py#L15-L16)
- [result.py:16](file://src/filtering/result.py#L16)
- [pipeline.py:93-93](file://src/filtering/pipeline.py#L93-L93)

### Examples of Relaxation Scenarios
- Budget widening: When a strict budget band yields fewer candidates than the minimum threshold, the system expands the budget bands and re-runs the pipeline.
- Keyword filter removal: When keyword filtering is too restrictive, removing it can yield more candidates.
- Minimum rating reduction: When the minimum rating is set too high for the available dataset, lowering it incrementally can improve candidate counts.
- Cuisine filter dropping: When cuisine filtering is overly restrictive, removing it maximizes candidate availability.

These scenarios are validated by tests demonstrating the relaxation steps and their outcomes.

**Section sources**
- [test_pipeline.py:76-97](file://tests/test_pipeline.py#L76-L97)
- [test_pipeline.py:100-117](file://tests/test_pipeline.py#L100-L117)
- [test_filters.py:92-95](file://tests/test_filters.py#L92-L95)

## Dependency Analysis
The relaxation logic depends on:
- Settings for min_candidates and max_candidates thresholds.
- UserPreferences for budget, cuisine, min_rating, and additional preferences.
- Filters for rating, cuisine, budget, keyword filtering, sorting, and truncation.
- FilterResult for returning the final state, including relaxation flags and steps.

```mermaid
graph TB
Settings["Settings<br/>(config.py)"]
UPref["UserPreferences<br/>(preferences.py)"]
FSvc["FilterService<br/>(pipeline.py)"]
Filt["Filters<br/>(filters.py)"]
FRes["FilterResult<br/>(result.py)"]
Settings --> FSvc
UPref --> FSvc
FSvc --> Filt
FSvc --> FRes
```

**Diagram sources**
- [config.py:46-71](file://src/config.py#L46-L71)
- [preferences.py:15-29](file://src/domain/preferences.py#L15-L29)
- [pipeline.py:34-40](file://src/filtering/pipeline.py#L34-L40)
- [filters.py:118-125](file://src/filtering/filters.py#L118-L125)
- [result.py:11-20](file://src/filtering/result.py#L11-L20)

**Section sources**
- [config.py:46-71](file://src/config.py#L46-L71)
- [preferences.py:15-29](file://src/domain/preferences.py#L15-L29)
- [pipeline.py:34-40](file://src/filtering/pipeline.py#L34-L40)
- [filters.py:118-125](file://src/filtering/filters.py#L118-L125)
- [result.py:11-20](file://src/filtering/result.py#L11-L20)

## Performance Considerations
- The pipeline logs warnings when execution exceeds a target duration, indicating potential performance bottlenecks.
- Each relaxation step involves re-running the pipeline, which can be computationally expensive depending on dataset size.
- Recommendations:
  - Tune min_candidates and max_candidates to balance candidate availability and performance.
  - Consider indexing strategies for city and cuisine filtering to reduce runtime.
  - Monitor empty_reason to detect scenarios where relaxation is frequently needed, signaling potential misalignment between user preferences and dataset characteristics.

**Section sources**
- [pipeline.py:88-89](file://src/filtering/pipeline.py#L88-L89)

## Troubleshooting Guide
Common issues and resolutions:
- No candidates returned: Check empty_reason and relaxation_steps to understand which filters were relaxed.
- Excessive relaxation: Review min_candidates and rating floor settings; adjust preferences to align with dataset distribution.
- Performance degradation: Investigate pipeline timing and consider reducing max_candidates or optimizing filters.

Validation references:
- Tests demonstrate relaxation behavior under various conditions, including budget widening and rating reduction scenarios.

**Section sources**
- [test_pipeline.py:76-117](file://tests/test_pipeline.py#L76-L117)
- [pipeline.py:93-93](file://src/filtering/pipeline.py#L93-L93)

## Conclusion
The relaxation mechanism provides a robust fallback strategy to ensure minimum candidate generation while maintaining transparency. By systematically widening budgets, removing restrictive filters, lowering rating thresholds, and finally dropping cuisine constraints, the system balances strict filtering with practical availability. Configurable parameters and detailed tracking enable operators to monitor and tune the behavior for optimal user experience.
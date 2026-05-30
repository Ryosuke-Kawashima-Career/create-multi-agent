# Sample Queries

Use these with the coordinator agent in ADK Web.

## Clear Request

```text
東京から一泊二日で、静かな田舎に行きたいです。公共交通で行けて、温泉があると嬉しいです。予算は3万円以内です。
```

Expected behavior: the agent should create 3 to 5 candidate policies, research each candidate with `google_search`, evaluate them, ask the user to choose one of the top 3 options, then create a detailed itinerary and bookmark image.

## Clarification Expected

```text
週末に一泊二日で温泉に行きたいです。静かで混みすぎない場所がいいです。
```

Expected behavior: because origin, budget, and transport are missing, the agent should ask for clarification with `RequestInput`. It should ask at most twice.

Suggested reply:

```text
出発地は東京、予算は一人3万円以内、公共交通で行きたいです。
```

## Reproposal

When the selection prompt appears, choose:

```text
4. 条件を変えて再提案。もう少し海が見える場所を優先してください。
```

Expected behavior: the agent should update the `TravelRequest`, create new options, and repeat research and evaluation.

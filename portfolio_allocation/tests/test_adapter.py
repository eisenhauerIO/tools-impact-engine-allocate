"""Integration tests for the MinimaxRegretAllocate adapter."""

from portfolio_allocation.adapter import MinimaxRegretAllocate


class TestAdapterContract:
    def test_result_keys(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        assert set(result.keys()) == {"selected_initiatives", "predicted_returns", "budget_allocated"}

    def test_selected_subset_of_input(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        input_ids = {i["initiative_id"] for i in sample_event["initiatives"]}
        assert set(result["selected_initiatives"]).issubset(input_ids)

    def test_budget_respected(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        total_allocated = sum(result["budget_allocated"].values())
        assert total_allocated <= sample_event["budget"]

    def test_predicted_returns_for_selected(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        assert set(result["predicted_returns"].keys()) == set(result["selected_initiatives"])

    def test_budget_allocated_for_selected(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        assert set(result["budget_allocated"].keys()) == set(result["selected_initiatives"])


class TestAdapterDeterminism:
    def test_repeated_calls_identical(self, sample_event):
        adapter = MinimaxRegretAllocate()
        r1 = adapter.execute(sample_event)
        r2 = adapter.execute(sample_event)
        assert r1 == r2


class TestAdapterEdgeCases:
    def test_budget_too_small(self, sample_event):
        sample_event["budget"] = 0.5
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        assert result["selected_initiatives"] == []

    def test_single_initiative(self):
        event = {
            "initiatives": [
                {
                    "initiative_id": "only",
                    "cost": 5,
                    "return_best": 10,
                    "return_median": 7,
                    "return_worst": 3,
                    "confidence": 0.9,
                }
            ],
            "budget": 10,
        }
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(event)
        assert result["selected_initiatives"] == ["only"]

    def test_all_filtered_by_confidence(self, sample_event):
        adapter = MinimaxRegretAllocate(min_confidence_threshold=1.0)
        result = adapter.execute(sample_event)
        assert result["selected_initiatives"] == []


class TestAdapterFieldMapping:
    def test_roundtrip_id_preservation(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        input_ids = {i["initiative_id"] for i in sample_event["initiatives"]}
        for sid in result["selected_initiatives"]:
            assert sid in input_ids

    def test_predicted_returns_match_input(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        id_to_median = {i["initiative_id"]: i["return_median"] for i in sample_event["initiatives"]}
        for sid, ret in result["predicted_returns"].items():
            assert ret == id_to_median[sid]

    def test_budget_allocated_matches_cost(self, sample_event):
        adapter = MinimaxRegretAllocate()
        result = adapter.execute(sample_event)
        id_to_cost = {i["initiative_id"]: i["cost"] for i in sample_event["initiatives"]}
        for sid, cost in result["budget_allocated"].items():
            assert cost == id_to_cost[sid]

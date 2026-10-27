from PrecedenteSearchApp import extrair_texto_resposta, preparar_tools


def test_collection_search_vira_file_search_na_responses_api():
    tools, usar_responses = preparar_tools([
        {
            "type": "collection_search",
            "collection_id": "collection_abc",
            "search_parameters": {"search_type": "hybrid", "top_k": 5},
        }
    ])

    assert usar_responses is True
    assert tools == [
        {
            "type": "file_search",
            "vector_store_ids": ["collection_abc"],
            "max_num_results": 5,
        }
    ]


def test_chat_sem_tools_permanece_em_chat_completions():
    tools, usar_responses = preparar_tools(None)
    assert tools is None
    assert usar_responses is False


def test_extrai_texto_da_responses_api():
    texto = extrair_texto_resposta({
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": "ok"}],
            },
        ]
    })
    assert texto == "ok"

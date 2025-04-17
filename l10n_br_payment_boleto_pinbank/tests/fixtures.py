GENERATE_BOLETO_PAYLOAD_DECRYPTED = {
    "Data": {
        "CodigoCanal": 10,
        "CodigoCliente": 1000,
        "DataVencimento": "20250422",
        "Valor": 25875,
        "Email": "atendimento@testeboleto.com.br",
        "DadosSacado": {
            "CpfCnpj": 73145637000140,
            "Nome": "Empresa Teste Boleto LTDA",
            "Endereco": "Rua Luiz Rubino",
            "Bairro": "Jardim Wilma Flor",
            "Cidade": "São Paulo",
            "Cep": 8473002,
            "Uf": "SP",
        },
        "RetornarBase64": True,
        "Instrucoes": "Não receber após o vencimento",
        "Juros": {
            "Valor": 100,
        },
        "Multa": {
            "Valor": 100,
        },
    }
}

GENERATE_BOLETO_PAYLOAD_ENCRYPTED = b"0GbmMs6BTPkvgdT/eXRGcu8KIo7lPq0GJMAzV0Wvi+P714xni+Oeirai5on7AY5jOsBrxrQBV1+/RAgc2FBiY/0gD5bLH11HjGhQhtDVohdSXxnQ5om4dwU9VA8eyYm6ftLIOwB/QqZl1uQo2NstbgGwNEi3IYzPxJ4wKdO/SlHSLcBRmxAO3/1b4S3dBuhFmvVxz+q8q1aI+bEwMCE1vQ+p65Hmh1Uf7fjaNzVAMK4mJc/hvoY8fbaJUbibEcq9FhiIb1fXGWKe8Hl8XqzpX+fXEDF5LBG9+BMVBr1OF9X5ebLStI2iP/QKxeIeBVo8HDdxSnVSVAryw8N7Xk9Cbz8qAsR7RuuBHSxBRRLO80UUBQQ3nWgoT9Twb7eTNa1gdJm6rZb8ELtYXI+V6A7aU3/QMj1zK6gxX/WnDqjuS9IAnNRHOTGeLtEOdMpl37iKbFYnYld+jXZ075Cp54ES0ggiksjTh1IMMxRM9tFTj6dv50eqPq0pMHqkai7ZSl4WS09OWoxFFEcBq6nh9F0RrORcwix7x4ka6aTIs/XsSDuDvhFJ8U++E0gBh6K6KugVGEHcTBP9sCwdTJxV2DhTC5/l1LEFN7WiMjdMNXvh718="  # noqa: E501,B950

SEND_CAPTURE_REQUEST_PAYLOAD = {
    "Data": {
        "CodigoCanal": 10,
        "CodigoCliente": 1000,
        "NossoNumero": "123456789",
    }
}

SEND_CAPTURE_REQUEST_RESPONSE = {
    "Data": {
        "Status": "PENDENTE",
        "Valor": 25875,
        "ValorPago": 0,
        "ValorJuros": 0,
        "ValorMulta": 0,
        "DataGeracao": "20250422",
        "DataVencimento": "20250422",
        "DataPagamento": "",
        "OrigemBoleto": "Site",
        "NossoNumero": "123456789",
        "LinhaDigitavel": "12345.67890 12345.678901 12345.678901 1 23456789012345",
        "CodigoBarras": "12345678901234567890123456789012345678901234",
        "IdentificadorCliente": None,
        "DadosPagador": {
            "CpfCnpj": 73145637000140,
            "Nome": "Empresa Teste Boleto LTDA",
            "Endereco": "Rua Luiz Rubino",
            "Bairro": "Jardim Wilma Flor",
            "Cidade": "São Paulo",
            "Cep": "08473002",
            "Uf": "SP",
            "DdiTerceiro": 0,
            "DddTerceiro": 0,
            "NumeroCelularTerceiro": 0,
        },
    }
}

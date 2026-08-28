#!/bin/bash
# Executa apenas os testes deste módulo
python -m pytest addons/helpdesk_description_optimizer/tests/ -v --tb=short 2>&1
# Alternativa Odoo nativo:
# ./odoo-bin -d test_db --test-enable --stop-after-init -i helpdesk_description_optimizer

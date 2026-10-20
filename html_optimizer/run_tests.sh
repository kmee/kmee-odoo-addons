#!/bin/bash
# Run only this module's tests.
# Pure-logic tests run standalone (no Odoo boot needed):
python -m unittest discover -s "$(dirname "$0")/tests" -p "test_*.py" -v 2>&1
# Native Odoo alternative (also runs any TransactionCase):
# ./odoo-bin -d test_db --test-enable --stop-after-init -i html_optimizer

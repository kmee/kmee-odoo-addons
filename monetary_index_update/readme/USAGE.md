This is a base/technical module that provides the infrastructure for monetary updates. 
It should be used together with other modules that implement the specific functionality 
for different system models.

## For End Users

The monetary update functionality will be made available through specific modules 
that extend this base module. Each implementing module may provide different ways 
to access the monetary correction feature (e.g., buttons, menu items, actions).

### Using Monetary Update on Records

When the functionality is implemented in a model, you will typically use a wizard to 
apply monetary corrections. The wizard allows you to:

1. **Select a Monetary Index**: Choose the economic index to use for correction 
   (e.g., SELIC, IPCA, INPC)
2. **Set the Start Date**: Define the original date of the monetary value
3. **Set the End Date**: Define the date to which you want to correct the value
4. **Preview Changes**: Review the updated values and percentage changes before applying
5. **Apply Correction**: Confirm to update the monetary values

> **Note**: The exact workflow and access method depends on how each specific module 
> implements the monetary update functionality. Refer to the documentation of the 
> module you are using for detailed instructions.

## Viewing Monetary Indexes

To view the monetary indexes available in the system:

1. Go to **Settings > Monetary Indexes**
2. View the list of registered indexes (SELIC, IPCA, INPC, etc.)
3. Click on an index to see its historical rates and detailed information

> **Note**: Standard users can only view indexes. 
> Only users with "Monetary Update Manager" permission can create, 
> edit, or delete indexes.

## For Monetary Update Managers

### Managing Monetary Indexes

1. Go to **Settings > Monetary Indexes**
2. Click **Create** to add a new index
3. Fill in the fields:
   - **Name**: Index name (e.g., "SELIC")
   - **Code**: Unique code (e.g., "selic")
   - **Authority**: Issuing authority (e.g., "BACEN", "IBGE")
   - **Country**: Country associated with the index
   - **Description**: Detailed information about the index

### Managing Historical Rates

1. Open a monetary index form
2. Go to the **Rates** tab
3. Add historical rates:
   - **Date**: Effective date of the rate
   - **Value**: Percentage value of the rate
   - **Source**: Data source (optional)
   - **Note**: Additional notes (optional)

## For Developers

To implement monetary correction in your custom modules, follow these steps:

### 1. Add Dependency

In your module's `__manifest__.py`:

```python
{
    "name": "Your Module",
    "depends": [
        "base_module",  # your existing dependencies
        "monetary_index_update",
    ],
    # ...
}
```

### 2. Extend Your Model

Inherit from `monetary.update.service` and specify which fields should be tracked:

```python
from odoo import models, fields

class YourModel(models.Model):
    _name = "your.model"
    _inherit = ["your.model", "monetary.update.service"]
    
    # Define which monetary fields should be updatable
    _fields_to_track = ["unit_price", "total_amount"]
    
    # Your model fields and methods...
```

### 3. Add UI Access

Provide a way for users to trigger the monetary update wizard. This can be done through:

**Option A - Button in tree/form view:**

```xml
<record id="view_your_model_tree_monetary" model="ir.ui.view">
    <field name="name">your.model.tree.monetary</field>
    <field name="model">your.parent.model</field>
    <field name="inherit_id" ref="your_module.view_your_model_tree"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='line_ids']/tree" position="inside">
            <button name="monetary_update_fields_by_index_wizard"
                    type="object"
                    icon="fa-calculator"
                    title="Update by Monetary Index"/>
        </xpath>
    </field>
</record>
```

**Option B - Action in context menu, or any other UI pattern that fits your use case.**

### 4. Using the Service Programmatically (Optional)

You can also use the monetary update service directly in your code:

```python
# Calculate updated amount
updated_amount = self.env["monetary.update.service"].compute_updated_amount(
    index_code="selic",
    amount=1000.00,
    start_date="2023-01-01",
    end_date="2024-01-01",
)
```

### Key Points

- The `_fields_to_track` attribute defines which monetary fields can be updated
- The wizard (`monetary_update_fields_by_index_wizard`) is automatically available once you inherit from `monetary.update.service`
- Users need appropriate permissions to see and use the monetary update functionality
- The wizard provides a preview before applying changes, allowing users to review the updated values

Refer to the source code and tests for complete implementation examples.

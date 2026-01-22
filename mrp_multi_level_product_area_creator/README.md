# MRP Multi Level Product Area Creator

## Description

This module provides a wizard to create Product MRP Areas for products and their BOM
components recursively.

## Features

- **Wizard Interface**: Easy-to-use wizard to select products and MRP area
- **Recursive BOM Processing**: Automatically processes all BOM components recursively
- **Duplicate Prevention**: Checks for existing Product MRP Areas to avoid duplicates
- **Detailed Logging**: Comprehensive logging for debugging and monitoring
- **User Feedback**: Clear success messages and result summaries

## Usage

1. Go to **Manufacturing > Planning > Create Product MRP Area**
2. Select the MRP Area where you want to create the Product MRP Areas
3. Select the products for which you want to create Product MRP Areas
4. Click **OK** to process

The wizard will:

- Find all BOM components recursively for the selected products
- Create Product MRP Area records for each component
- Skip products that already have Product MRP Areas in the selected MRP Area
- Show a summary of created and existing records

## Technical Details

### Models

- `product.mrp.area.create`: Transient model for the wizard

### Dependencies

- `mrp_multi_level`: Core MRP Multi Level functionality

### Security

- Users: Read access to the wizard
- Managers: Full access (read, write, create, unlink)

## Installation

1. Install the module from the Apps menu
2. The menu item will be available under Manufacturing > Planning

## License

AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

## Author

KMEE (https://www.kmee.com.br)

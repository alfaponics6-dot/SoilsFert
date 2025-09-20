# Modal Template Management System

This document explains how to use the new modal template management system in your SoilsFert application.

## Overview

The modal system provides a centralized way to manage all dialogs and modals in your application with:
- Consistent styling and behavior
- Accessibility features
- Easy integration
- Reusable components

## File Structure

```
templates/
├── base.html                          # Base template with modal support
├── includes/
│   ├── modal_manager.html            # Core modal management system
│   └── all_modals.html               # All modals included together
├── modals/
│   ├── login_required.html           # Login requirement modal
│   ├── confirmation.html             # Confirmation dialog
│   ├── success.html                  # Success messages
│   └── loading.html                  # Loading indicators
└── pages/
    └── dashboard.html                # Example page using modals
```

## Quick Start

### 1. Update Your Templates

Replace your existing template structure with the new system:

```python
# In your Flask routes, use render_template instead of render_template_string
@app.route('/dashboard')
@login_required
def dashboard():
    analyses = get_user_analyses(session['user_id'])
    return render_template('pages/dashboard.html', analyses=analyses)
```

### 2. Include Modals in Your Pages

Add this to any page that needs modals:

```html
{% extends "base.html" %}

{% block modals %}
{% include 'includes/all_modals.html' %}
{% endblock %}
```

### 3. Use Modal Functions

#### Show Login Required Modal
```javascript
// For sharing features that require login
AppModals.showLoginForSharing();

// Or use the generic version
ModalUtils.requireLogin();
```

#### Show Confirmation Dialog
```javascript
AppModals.confirmDelete('Analysis Report', () => {
    // Delete action here
    window.location.href = '/delete/123';
});

// Or custom confirmation
ModalUtils.confirm({
    title: 'Custom Action',
    message: 'Are you sure?',
    confirmText: 'Yes, Do It',
    callback: () => { /* action */ }
});
```

#### Show Success Messages
```javascript
AppModals.showAnalysisComplete('12345');

// Or custom success
ModalUtils.success({
    title: 'Success!',
    message: 'Operation completed successfully.',
    autoHide: true
});
```

#### Show Loading Indicators
```javascript
AppModals.showAnalysisLoading();

// Update progress
ModalUtils.updateLoadingProgress(50, 'Processing data...');

// Hide when done
ModalUtils.hideLoading();
```

#### Show Error Messages
```javascript
ModalUtils.error({
    title: 'Error',
    message: 'Something went wrong.',
    confirmText: 'Retry'
});
```

## HTML Attributes for Easy Integration

### Require Login
Add `data-requires-login` to any button that requires authentication:

```html
<button data-requires-login onclick="shareExperience()">
    Share Experience
</button>
```

### Confirm Delete
Add `data-confirm-delete` to delete buttons:

```html
<button data-confirm-delete 
        data-item-name="Soil Analysis" 
        data-delete-url="/delete/123">
    Delete
</button>
```

## Customization

### Custom Modal Styles
Add custom styles in your template:

```html
{% block custom_styles %}
{{ super() }}
.my-custom-modal {
    /* Custom styles */
}
{% endblock %}
```

### Custom Modal Functions
Create application-specific modal functions:

```javascript
const MyAppModals = {
    showPaymentSuccess(amount) {
        ModalUtils.success({
            title: 'Payment Successful!',
            message: `Payment of $${amount} has been processed.`,
            details: 'You will receive a confirmation email shortly.'
        });
    }
};
```

## Migration from Existing System

### Step 1: Replace render_template_string
```python
# Old way
return render_template_string(DASHBOARD_TEMPLATE, data=data)

# New way
return render_template('pages/dashboard.html', data=data)
```

### Step 2: Update Modal Calls
```javascript
// Old way (if you had custom modals)
showCustomModal('loginRequired');

// New way
AppModals.showLoginForSharing();
```

### Step 3: Move Template Content
Move your existing template strings to separate HTML files in the templates directory.

## Benefits

1. **Maintainability**: All modals are in separate files, easy to edit
2. **Consistency**: Uniform styling and behavior across all modals
3. **Accessibility**: Built-in keyboard navigation and focus management
4. **Reusability**: Common modal patterns available as simple function calls
5. **Performance**: Templates are cached by Flask
6. **Development**: Easier to debug and modify individual components

## Advanced Usage

### Custom Modal Creation
Create new modal templates in the `templates/modals/` directory and include them in `all_modals.html`.

### Event Handling
Listen for modal events:

```javascript
document.getElementById('myModal').addEventListener('modalShown', (e) => {
    console.log('Modal shown with options:', e.detail);
});
```

### Integration with Forms
```javascript
function handleFormSubmit(form) {
    const formData = new FormData(form);
    
    // Show loading
    ModalUtils.loading({
        title: 'Saving...',
        message: 'Please wait while we save your data.'
    });
    
    // Submit form (example with fetch)
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        ModalUtils.hideLoading();
        if (data.success) {
            ModalUtils.success({
                title: 'Saved!',
                message: 'Your data has been saved successfully.'
            });
        } else {
            ModalUtils.error({
                title: 'Error',
                message: data.message || 'An error occurred.'
            });
        }
    })
    .catch(error => {
        ModalUtils.hideLoading();
        ModalUtils.error({
            title: 'Network Error',
            message: 'Please check your connection and try again.'
        });
    });
}
```

This system provides a robust foundation for managing all modal interactions in your application while maintaining clean, maintainable code.

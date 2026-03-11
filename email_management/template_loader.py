"""
Utility module for loading and rendering HTML email templates.
"""
import os
import re
from django.conf import settings


class EmailTemplateLoader:
    """
    Load HTML email templates and replace variables.
    """
    
    TEMPLATE_DIR = os.path.join(
        settings.BASE_DIR,
        'email_management',
        'templates',
        'email_templates'
    )
    
    @classmethod
    def get_available_templates(cls):
        """
        Get list of available email templates organized by category.
        
        Returns:
            dict: {category: [template_files]}
        """
        templates = {}
        
        for category in ['common', 'district-emails']:
            category_path = os.path.join(cls.TEMPLATE_DIR, category)
            if os.path.exists(category_path):
                templates[category] = []
                for filename in os.listdir(category_path):
                    if filename.endswith('.html'):
                        templates[category].append({
                            'name': filename.replace('.html', '').replace('-', ' ').title(),
                            'filename': filename,
                            'category': category,
                            'path': f'{category}/{filename}'
                        })
        
        return templates
    
    @classmethod
    def load_template(cls, category, filename):
        """
        Load a template file.
        
        Args:
            category: Template category (common or district-emails)
            filename: Template filename (e.g., welcome.html)
        
        Returns:
            str: HTML content
        """
        template_path = os.path.join(cls.TEMPLATE_DIR, category, filename)
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template not found: {category}/{filename}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @classmethod
    def get_template_variables(cls, html_content):
        """
        Extract all variables from template ({{variable_name}}).
        
        Args:
            html_content: HTML string
        
        Returns:
            list: Variable names
        """
        pattern = r'\{\{(\w+)\}\}'
        matches = re.findall(pattern, html_content)
        return list(set(matches))  # Remove duplicates
    
    @classmethod
    def render_template(cls, html_content, variables):
        """
        Replace variables in template with actual values.
        
        Args:
            html_content: HTML string with {{variable}} placeholders
            variables: dict of variable_name: value
        
        Returns:
            str: Rendered HTML
        """
        rendered = html_content
        
        for var_name, value in variables.items():
            placeholder = f'{{{{{var_name}}}}}'
            rendered = rendered.replace(placeholder, str(value or ''))
        
        return rendered

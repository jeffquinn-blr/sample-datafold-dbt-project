{% macro create_udfs() %}
    create schema if not exists {{target.schema}};
{% endmacro %}

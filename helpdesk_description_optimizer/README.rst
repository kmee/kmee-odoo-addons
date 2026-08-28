===============================
Helpdesk Description Optimizer
===============================

Módulo Odoo para otimização do campo description em tickets Helpdesk.

Funcionalidades
===============

* Sanitização de HTML no campo description
* Remoção de caracteres zero-width (U+FEFF, U+200B, etc.)
* Normalização de estilos de imagem (remove width/height em in/cm)
* Remoção de blocos duplicados (ex: disclaimers de e-mail)
* Colapso de parágrafos vazios consecutivos
* Truncagem de HTML grande (>50KB) mantendo validade do HTML
* Campo description_full para armazenar HTML original completo
* Interface JavaScript para:
  - Colapsar threads de e-mail
  - Lazy loading de imagens
  - Botão "Ver conteúdo completo"

Instalação
==========

Instale via Apps do Odoo ou copie para o diretório de addons.

Configuração
============

Nenhuma configuração adicional necessária.

Uso
===

O módulo atua automaticamente ao criar ou editar tickets Helpdesk.

Créditos
========

* Autor: KMEE

Licença
=======

LGPL-3

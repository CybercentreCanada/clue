{: set filetype=mustache: */}}

{{/*
image_name
Returns the full image name for a plugin, using the following logic:
1. If .image.name is set, use it
2. Otherwise, build the image name as:
   {{ $.Values.images.rest.plugin_repository | default $.Values.images.rest.repository }}/{{ .name }}-plugin
Appends the image tag, defaulting to 'main' if not set.
Usage: {{ include "image_name" (dict "plugin" . "Values" $.Values) }}
*/}}
{{- define "image_name" -}}
{{- $plugin := .plugin -}}
{{- $Values := .Values -}}
{{- $imageName := "" -}}
{{- if $plugin.image.name -}}
  {{- $imageName = $plugin.image.name -}}
{{- else -}}
  {{- $repository := $Values.images.rest.plugin_repository | default $Values.images.rest.repository -}}
  {{- $imageName = printf "%s/clue-plugin-%s" $repository $plugin.name -}}
{{- end -}}
{{- $imageTag := $plugin.image.tag | default "main" -}}
{{- printf "%s:%s" $imageName $imageTag -}}
{{- end -}}

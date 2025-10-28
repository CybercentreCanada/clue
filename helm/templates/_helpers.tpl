{: set filetype=mustache: */}}

{{/*
Expand the name of the chart.
*/}}
{{- define "clue.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "clue.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "clue.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "clue.labels" -}}
app.kubernetes.io/name: {{ include "clue.name" . }}
helm.sh/chart: {{ include "clue.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

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

{{/*
printConfigs
takes a section of values and prints it in dot notation instead of the hierarchy
*/}}
{{- define "printConfigs" }}
  {{- if kindIs "map" .map }}
    {{- range $key, $map := .map }}
      {{- include "printConfigs" (dict "key" (append $.key $key ) "map" $map) }}
    {{- end -}}
  {{- else -}}
    {{printf "%s=%s\n" (join "." .key) (toString .map) }}
  {{- end -}}
{{- end }}

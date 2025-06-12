{{/*
Expand the name of the chart.
*/}}
{{- define "ingestion-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ingestion-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ingestion-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ingestion-api.labels" -}}
helm.sh/chart: {{ include "ingestion-api.chart" . }}
{{ include "ingestion-api.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: ingestion-api
app.kubernetes.io/part-of: loom
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ingestion-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ingestion-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ingestion-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "ingestion-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the image reference
*/}}
{{- define "ingestion-api.image" -}}
{{- $registry := .Values.image.registry -}}
{{- if .Values.global.imageRegistry -}}
{{- $registry = .Values.global.imageRegistry -}}
{{- end -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- else -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}
{{- end }}

{{/*
Create environment from global and local config
*/}}
{{- define "ingestion-api.environment" -}}
{{- if .Values.global.environment -}}
{{- .Values.global.environment -}}
{{- else -}}
{{- .Values.config.environment -}}
{{- end -}}
{{- end }}

{{/*
Create ConfigMap name
*/}}
{{- define "ingestion-api.configMapName" -}}
{{- if .Values.configMap.name -}}
{{- .Values.configMap.name -}}
{{- else -}}
{{- printf "%s-config" (include "ingestion-api.fullname" .) -}}
{{- end -}}
{{- end }}

{{/*
Create Secret name
*/}}
{{- define "ingestion-api.secretName" -}}
{{- if .Values.secret.name -}}
{{- .Values.secret.name -}}
{{- else -}}
{{- printf "%s-secret" (include "ingestion-api.fullname" .) -}}
{{- end -}}
{{- end }}

{{/*
Create PVC name
*/}}
{{- define "ingestion-api.pvcName" -}}
{{- if .Values.persistence.name -}}
{{- .Values.persistence.name -}}
{{- else -}}
{{- printf "%s-data" (include "ingestion-api.fullname" .) -}}
{{- end -}}
{{- end }}

{{/*
Validate configuration
*/}}
{{- define "ingestion-api.validateConfig" -}}
{{- if not .Values.config.kafka.bootstrapServers -}}
{{- fail "config.kafka.bootstrapServers is required" -}}
{{- end -}}
{{- if not .Values.config.kafka.audioTopic -}}
{{- fail "config.kafka.audioTopic is required" -}}
{{- end -}}
{{- if not .Values.config.kafka.sensorTopic -}}
{{- fail "config.kafka.sensorTopic is required" -}}
{{- end -}}
{{- end -}} 
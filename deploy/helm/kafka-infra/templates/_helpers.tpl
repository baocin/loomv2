{{/*
Common template helpers for kafka-infra chart
*/}}

{{- define "kafka-infra.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kafka-infra.fullname" -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s-%s" (include "kafka-infra.name" .) (default .Release.Name .Values.fullnameOverride) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "kafka-infra.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "kafka-infra.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "kafka-infra.selectorLabels" -}}
app.kubernetes.io/name: {{ include "kafka-infra.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}} 
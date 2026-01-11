{{/*
Expand the name of the chart.
*/}}
{{- define "ops-agents.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "ops-agents.fullname" -}}
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
{{- define "ops-agents.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "ops-agents.labels" -}}
helm.sh/chart: {{ include "ops-agents.chart" . }}
{{ include "ops-agents.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "ops-agents.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ops-agents.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Gateway labels
*/}}
{{- define "ops-agents.gateway.labels" -}}
{{ include "ops-agents.labels" . }}
app.kubernetes.io/component: gateway
{{- end }}

{{/*
Gateway selector labels
*/}}
{{- define "ops-agents.gateway.selectorLabels" -}}
{{ include "ops-agents.selectorLabels" . }}
app.kubernetes.io/component: gateway
{{- end }}

{{/*
Orchestrator labels
*/}}
{{- define "ops-agents.orchestrator.labels" -}}
{{ include "ops-agents.labels" . }}
app.kubernetes.io/component: orchestrator
{{- end }}

{{/*
Orchestrator selector labels
*/}}
{{- define "ops-agents.orchestrator.selectorLabels" -}}
{{ include "ops-agents.selectorLabels" . }}
app.kubernetes.io/component: orchestrator
{{- end }}

{{/*
Otel Collector labels
*/}}
{{- define "ops-agents.otelCollector.labels" -}}
{{ include "ops-agents.labels" . }}
app.kubernetes.io/component: otel-collector
{{- end }}

{{/*
Otel Collector selector labels
*/}}
{{- define "ops-agents.otelCollector.selectorLabels" -}}
{{ include "ops-agents.selectorLabels" . }}
app.kubernetes.io/component: otel-collector
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "ops-agents.gateway.serviceAccountName" -}}
{{- if .Values.serviceAccount.gateway.create }}
{{- default (printf "%s-gateway" (include "ops-agents.fullname" .)) .Values.serviceAccount.gateway.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.gateway.name }}
{{- end }}
{{- end }}

{{- define "ops-agents.orchestrator.serviceAccountName" -}}
{{- if .Values.serviceAccount.orchestrator.create }}
{{- default (printf "%s-orchestrator" (include "ops-agents.fullname" .)) .Values.serviceAccount.orchestrator.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.orchestrator.name }}
{{- end }}
{{- end }}

{{- define "ops-agents.otelCollector.serviceAccountName" -}}
{{- if .Values.serviceAccount.otelCollector.create }}
{{- default (printf "%s-otel-collector" (include "ops-agents.fullname" .)) .Values.serviceAccount.otelCollector.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.otelCollector.name }}
{{- end }}
{{- end }}


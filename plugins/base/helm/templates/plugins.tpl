{{- range .Values.plugins -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .name }}
  labels:
    app.kubernetes.io/component: plugin
    app.kubernetes.io/name: {{ .name }}
    helm.sh/chart: {{ $.Chart.Name }}-{{ $.Chart.Version }}
    app.kubernetes.io/instance: {{ $.Release.Name }}
    {{- if $.Chart.AppVersion }}
    app.kubernetes.io/version: {{ $.Chart.AppVersion | quote }}
    {{- end }}
    app.kubernetes.io/managed-by: {{ $.Release.Service }}
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: {{.name}}
      app.kubernetes.io/instance: {{ $.Release.Name }}
      app.kubernetes.io/version: {{ $.Chart.AppVersion }}
  template:
    metadata:
      labels:
        app.kubernetes.io/component: plugin
        app.kubernetes.io/name: {{.name}}
        app.kubernetes.io/instance: {{ $.Release.Name }}
        app.kubernetes.io/version: {{ $.Chart.AppVersion }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/plugin-config.yaml") $ | sha256sum }}
    spec:
      nodeSelector:
{{ toYaml $.Values.nodeSelector | indent 8 }}
      affinity:
{{ toYaml $.Values.affinity | indent 8 }}
      tolerations:
{{ toYaml $.Values.tolerations | indent 8 }}
      containers:
      - name: {{.name}}
        image: "{{ include "image_name" (dict "plugin" . "Values" $.Values) }}"
        imagePullPolicy: {{ .image.pullPolicy | quote }}
        ports:
        - containerPort: 5000
        volumeMounts:
        - name: conf
          mountPath: "/etc/{{ .name }}/conf/"
        env:
        - name: APP_NAME
          value: {{ .name }}
        - name: REQUESTS_CA_BUNDLE
          value: /etc/ssl/certs/ca-certificates.crt
        - name: WORKERS
          value: "12"
        - name: THREADS
          value: "4"
        - name: EXECUTOR_THREADS
          value: "16"
        - name: WORKER_CONNECTIONS
          value: "2048"
        - name: LIMIT_REQUEST_FIELD_SIZE
          value: "16380"
        - name: CACHE_TYPE
          value: {{ .cache_type | default "redis" }}
        - name: CENTRAL_API_URL
          value: {{ $.Values.rest.full_url }}
        {{- if $.Values.redis.auth.enabled }}
        - name: CORE__REDIS__PASSWORD
          valueFrom:
            secretKeyRef:
              name: clue-redis
              key: redis-password
        {{- end }}
{{- if .env }}
{{ tpl (toYaml .env) $ | indent 8 }}
{{- end }}
        resources:
          {{- toYaml $.Values.resources | nindent 10 }}
      volumes:
      - name: conf
        configMap:
          name: clue-plugin-conf-{{ .name }}
---

apiVersion: v1
kind: Service
metadata:
  name: {{ .name }}-plugin
  labels:
    app: {{ .name }}-plugin
spec:
  type: ClusterIP
  ports:
  - port: {{ .port | default 5000 }}
    targetPort: 5000
    protocol: TCP
    name: plugin
  selector:
    app.kubernetes.io/name: {{ .name }}
    app.kubernetes.io/instance: {{ $.Release.Name }}
    app.kubernetes.io/component: plugin
---

{{- if .ingress -}}
{{- $prefix := .name -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .name }}
  labels:
{{ include "clue.labels" $ | indent 4 }}
  {{- with $.Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  tls:
    {{- range $.Values.ingress.tls }}
    - hosts:
      {{- range $host := .hosts | default (list "") }}
        - "{{ $prefix }}-{{ $host }}"
      {{- end }}
      secretName: {{.secretName}}
    {{- end }}
  rules:
    {{- range $host := $.Values.ingress.hosts | default (list "") }}
    - host: "{{ $prefix }}-{{ $host }}"
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ $prefix }}-plugin
                port:
                  name: plugin
    {{- end }}
{{- end }}
---

{{- if $.Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ .name }}
  labels: {}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ .name }}
  minReplicas: {{ $.Values.autoscaling.minReplicas }}
  maxReplicas: {{ $.Values.autoscaling.maxReplicas }}
  {{- if $.Values.autoscaling.metrics }}
  metrics:
  {{- toYaml $.Values.autoscaling.metrics | nindent 4}}
  {{- end }}
  {{- if $.Values.autoscaling.behavior }}
  behavior:
  {{- toYaml $.Values.autoscaling.behavior | nindent 4 }}
  {{- end }}
{{- end }}
---

{{- if .extraResources }}
  {{- range $resource := .extraResources }}
    # this bit allows plugin devs to include arbitrary kubernetes resources in their values
    {{- tpl (toYaml $resource) $ | nindent 0 }}
---
  {{- end }}
{{- end }}

{{- end -}}

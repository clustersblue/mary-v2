<template>
  <GenericSettingsView
    title="Care Services Catalog"
    entityName="Care Service"
    apiEndpoint="/services"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>

<template>
  <GenericSettingsView
    title="NHS Commissioners & ICB Trusts"
    entityName="NHS Commissioner"
    apiEndpoint="/nhs"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>

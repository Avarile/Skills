You don't have a dedicated note on Kubernetes node labels, but node labels come up in two of your **K3S** knowledge entries (you keep your Kubernetes notes under "K3S"/"K8S" titles):

### 1. K3S - Cheatsheet (#47), section "3. Node Management" (last updated 2026-10-05)
The generic commands:

```bash
# Get node labels
kubectl get node <node-name> --show-labels

# Add label to node
kubectl label node <node-name> key=value

# Remove label from node
kubectl label node <node-name> key-
```

The same section also covers taints (`kubectl taint node <node-name> key=value:NoSchedule|NoExecute|PreferNoSchedule`, remove with `key:NoSchedule-`), plus cordon/uncordon/drain.

Section **"20. Labels, Annotations & Selectors"** adds:
- `kubectl label node <name> key=value`
- Update an existing label: `kubectl label pod <name> key=newvalue --overwrite`
- Selector filtering: `-l app=nginx,env=prod`, `-l 'env in (prod,staging)'`, `-l 'env notin (dev)'`, `-l 'app'` (has the key)

### 2. K3S - Create new service (#46), section "12. Node Management" (2026-06-07)
The same commands written for your cluster (`workstation` + `fedora` nodes):

```bash
# Label a node (useful for node affinity rules)
kubectl label node workstation role=infra

# Remove a label from a node
kubectl label node workstation role-
```

Next to it you noted tainting `fedora` for maintenance (`kubectl taint nodes fedora maintenance=true:NoSchedule`, remove with a trailing `-`).

So the one real label you wrote down is **`role=infra` on the `workstation` node**, meant for node affinity. I didn't find a nodeSelector/affinity manifest that actually uses it in your notes. Your other K3S entries (HomeLab init, Data: Management, Migration script, K3s-Infras) don't mention node labels.

Want me to pull up either entry in full?

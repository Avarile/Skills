You wrote about node labels in your **K3S - Cheatsheet** (`rec9TTSDoktu59fT89i`, type *k3s - operation*). The relevant commands are in two sections.

**§3 Node Management**

```bash
# Get node labels
kubectl get node <node-name> --show-labels

# Add label to node
kubectl label node <node-name> key=value

# Remove label from node
kubectl label node <node-name> key-
```

The same section also covers taints, which are the related way to steer scheduling:
`kubectl taint node <node-name> key=value:NoSchedule` (also `NoExecute` / `PreferNoSchedule`), and you remove one with `kubectl taint node <node-name> key:NoSchedule-`.

**§20 Labels, Annotations & Selectors**

- Add: `kubectl label node <name> key=value`
- Change an existing value: add `--overwrite` (your example uses a pod: `kubectl label pod <name> key=newvalue --overwrite`)
- Filter by selector: `-l app=nginx`, `-l 'env in (prod,staging)'`, `-l 'env notin (dev)'`, `-l 'app'` (has key). Your examples use pods, but `-l` works the same on `kubectl get nodes`.
- Pods on a given node: `kubectl get pods --field-selector=spec.nodeName=<node>`

The cheatsheet doesn't cover using node labels for scheduling (`nodeSelector` or node affinity in a pod spec). A search for `nodeSelector` found nothing in the knowledge base.

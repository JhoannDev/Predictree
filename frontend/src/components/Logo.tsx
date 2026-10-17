import styles from "./Logo.module.css";

interface LogoProps {
  variante?: "claro" | "oscuro";
}

export default function Logo({ variante = "oscuro" }: LogoProps) {
  return (
    <span className={`${styles.logo} ${variante === "claro" ? styles.claro : styles.oscuro}`}>
      PredicTree<span className={styles.punto}>.</span>
    </span>
  );
}

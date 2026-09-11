import argparse

from agente import clasificar_ticket


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticket", required=True, help="Texto del ticket a clasificar")
    args = parser.parse_args()

    urgencia = clasificar_ticket(args.ticket)
    print(f"urgencia: {urgencia}")


if __name__ == "__main__":
    main()

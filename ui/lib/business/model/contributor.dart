class Contributor {
  String name;
  String email;
  List<Contributor> aliases = [];

  Contributor({
    required this.name,
    required this.email,
  });

  static Contributor from(List<String> aliases) {
    var c = Contributor(
      name: aliases[0].split('<').first.trim(),
      email: aliases[0].split('<').last.split('>').first.trim(),
    );
    for (var i = 1; i < aliases.length; i++) {
      c.aliases.add(Contributor(
        name: aliases[i].split('<').first.trim().substring(1),
        email: aliases[i].split('<').last.split('>').first.trim().substring(1),
      ));
    }
    return c;
  }
}

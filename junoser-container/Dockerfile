FROM ubuntu:20.04

RUN apt update
RUN apt install -y sed git ruby bundler zlib1g-dev
RUN apt clean

RUN git clone https://github.com/codeout/junoser.git
WORKDIR /junoser
RUN mkdir /junoser/tmp

ADD junos.xsd /junoser/tmp/junos.xsd
ADD lint-structured /usr/local/bin/lint-structured
RUN sed -i "s#^xsd_path.*#xsd_path = File.join(__dir__, 'tmp/junos.xsd')#" /junoser/Rakefile

RUN bundle install
RUN bundle exec rake build:config build:rule

CMD ["/junoser/exe/junoser", "-d", "/generated.txt"]